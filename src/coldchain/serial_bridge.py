"""Ponte serial: le as linhas da Heltec receptora e entrega os pacotes ao gateway.

Protocolo (Secao 9.3), uma linha por evento, 115200 8N1:
  RX,<rssi>,<snr>,<hex>   pacote recebido
  INFO,<texto>            mensagem informativa
  ERR,<codigo>,<texto>    erro do radio
Linhas com outro prefixo ou malformadas sao ignoradas; a ponte nunca cai por causa delas.

Uso:
  python -m coldchain.serial_bridge --simulate          # sem hardware
  python -m coldchain.serial_bridge --port /dev/ttyUSB0 # com a Heltec receptora
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

from . import crypto
from .config import Config, load_config, load_trusted_keys
from .gateway import Gateway, Outcome
from .ledger import Ledger
from .node_sim import SimNode
from .packet import STATUS_NAMES

log = logging.getLogger("coldchain.bridge")

MAX_HEX_LEN = 2 * 255  # limite de payload do LoRa


@dataclass(frozen=True)
class SerialLine:
    kind: str  # "RX", "INFO" ou "ERR"
    data: bytes = b""
    rssi: int | None = None
    snr: float | None = None
    code: str | None = None
    text: str = ""


def parse_line(line: str | bytes) -> SerialLine | None:
    """Interpreta uma linha do receptor. Devolve None para linha invalida (nunca levanta)."""
    try:
        if isinstance(line, bytes):
            line = line.decode("ascii", errors="replace")
        line = line.strip()
        if line.startswith("RX,"):
            parts = line.split(",")
            if len(parts) != 4:
                return None
            _, rssi, snr, hexdata = parts
            if len(hexdata) % 2 or len(hexdata) > MAX_HEX_LEN:
                return None
            return SerialLine("RX", bytes.fromhex(hexdata), int(rssi), float(snr))
        if line.startswith("INFO,"):
            return SerialLine("INFO", text=line[5:])
        if line.startswith("ERR,"):
            parts = line.split(",", 2)
            return SerialLine("ERR", code=parts[1], text=parts[2] if len(parts) > 2 else "")
    except (ValueError, IndexError):
        return None
    return None


def format_rx_line(packet: bytes, rssi: int, snr: float) -> str:
    """Linha exatamente como o firmware do receptor escreve."""
    return f"RX,{rssi},{snr:.1f},{packet.hex()}"


@dataclass
class BridgeStats:
    lines: int = 0
    ignored: int = 0
    rx: int = 0
    info: int = 0
    errors: int = 0
    connected: bool = False
    source: str = ""
    last_line_at: float | None = None
    last_info: str = ""


class SerialBridge:
    """Liga uma fonte de linhas (serial real ou simulada) ao gateway."""

    def __init__(self, gateway: Gateway, on_outcome: Callable[[Outcome], None] | None = None):
        self.gateway = gateway
        self.on_outcome = on_outcome
        self.stats = BridgeStats()

    def handle_line(self, line: str | bytes) -> Outcome | None:
        self.stats.lines += 1
        self.stats.last_line_at = time.time()
        parsed = parse_line(line)
        if parsed is None:
            self.stats.ignored += 1
            log.debug("linha ignorada: %r", line)
            return None
        if parsed.kind == "INFO":
            self.stats.info += 1
            self.stats.last_info = parsed.text
            log.info("receptor: %s", parsed.text)
            return None
        if parsed.kind == "ERR":
            self.stats.errors += 1
            log.warning("erro do radio %s: %s", parsed.code, parsed.text)
            return None
        self.stats.rx += 1
        out = self.gateway.receive(parsed.data, rssi=parsed.rssi, snr=parsed.snr)
        r = out.reading
        log.info(
            "RX %d bytes rssi=%s snr=%s -> %s%s",
            len(parsed.data), parsed.rssi, parsed.snr, out.result.value,
            f" (no {r.node_id} seq {r.seq} T={r.temp_c:.2f}C {STATUS_NAMES[r.status]})" if r else "",
        )
        if self.on_outcome:
            self.on_outcome(out)
        return out

    def run(self, lines: Iterable[str | bytes], stop: threading.Event | None = None) -> None:
        stop = stop or threading.Event()
        for line in lines:
            if stop.is_set():
                break
            try:
                if line:
                    self.handle_line(line)
                self.gateway.check_silence()
            except Exception:  # a ponte nao pode cair (ex.: banco travado)
                log.exception("erro ao processar linha %r", line)


def serial_lines(
    port: str,
    baud: int,
    stats: BridgeStats,
    stop: threading.Event,
    reconnect_s: float = 2.0,
) -> Iterator[bytes]:
    """Linhas da porta serial, com reconexao automatica se a Heltec for desligada."""
    import serial  # pyserial, so necessario com hardware

    stats.source = port
    while not stop.is_set():
        try:
            with serial.Serial(port, baud, timeout=1) as ser:
                stats.connected = True
                log.info("serial conectada: %s @ %d", port, baud)
                while not stop.is_set():
                    # b"" no timeout: permite ao laco checar silencio mesmo sem pacotes
                    yield ser.readline()
        except (serial.SerialException, OSError) as e:
            if stats.connected:
                log.warning("serial desconectada: %s", e)
            stats.connected = False
            stop.wait(reconnect_s)
    stats.connected = False


class SimulatedReceiver:
    """Gera linhas RX,... a partir de um SimNode, como se viessem da Heltec receptora.

    A temperatura segue um passeio aleatorio em torno de `target`. `heat(True)` muda o alvo
    para fora da faixa (simula a mao no sensor) para provocar ALERTA e ALARME.
    """

    def __init__(self, node: SimNode, interval_s: float = 2.0, seed: int | None = 42):
        self.node = node
        self.interval_s = interval_s
        self.rng = random.Random(seed)
        self.temp = 5.0
        self.target = 5.0
        self.lock = threading.Lock()

    def heat(self, on: bool) -> None:
        with self.lock:
            self.target = 10.0 if on else 5.0

    @property
    def heating(self) -> bool:
        return self.target > 8.0

    def next_line(self) -> str:
        with self.lock:
            self.temp += 0.35 * (self.target - self.temp) + self.rng.gauss(0, 0.12)
            temp = round(self.temp, 2)
        hum = round(45 + self.rng.gauss(0, 1.5), 2)
        pkt = self.node.make_packet(temp, hum_pct=hum, lat=-10.9472, lon=-37.0731)
        rssi = int(-60 + self.rng.gauss(0, 3))
        snr = round(9.5 + self.rng.gauss(0, 0.8), 1)
        return format_rx_line(pkt, rssi, snr)

    def lines(self, stats: BridgeStats, stop: threading.Event) -> Iterator[str]:
        stats.connected = True
        stats.source = "simulado"
        yield "INFO,receptor simulado 915.0MHz SF7 BW125 CR4/5"
        while not stop.is_set():
            yield self.next_line()
            stop.wait(self.interval_s)
        stats.connected = False


def make_sim_node(cfg: Config, gateway: Gateway) -> SimNode:
    """No simulado. Usa keys/private/node_<id>.pem se existir; senao, chave efemera
    registrada so na memoria do gateway."""
    node_id = cfg.sim.node_id
    pem_path = cfg.resolve(os.path.join("keys", "private", f"node_{node_id}.pem"))
    if os.path.exists(pem_path):
        with open(pem_path, "rb") as f:
            key = crypto.private_from_pem(f.read())
    else:
        key = crypto.generate_keypair()
    gateway.keys[node_id] = key.public_key()
    return SimNode(node_id, key, cfg.thresholds, seed=cfg.sim.seed)


def build_gateway(cfg: Config, db_path: str | None = None) -> Gateway:
    ledger = Ledger(cfg.resolve(db_path or cfg.db_path))
    keys = load_trusted_keys(cfg.resolve(cfg.keys_file))
    return Gateway(
        ledger, keys, cfg.thresholds,
        expected_interval_s=cfg.node.expected_interval_s,
        silence_factor=cfg.node.silence_factor,
        allow_resync=cfg.allow_resync,
    )


def setup_logging(cfg: Config, verbose: bool = False) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if cfg.log_file:
        path = cfg.resolve(cfg.log_file)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", help="caminho do config.toml")
    p.add_argument("--port", help="porta serial (ex.: /dev/ttyACM0)")
    p.add_argument("--baud", type=int)
    p.add_argument("--db", help="caminho do banco SQLite (':memory:' para nao gravar)")
    p.add_argument("--simulate", action="store_true", help="gera pacotes sem hardware")
    p.add_argument("--allow-resync", action="store_true",
                   help="permite --reset-node (desligado por padrao)")
    p.add_argument("--reset-node", type=int, metavar="ID",
                   help="registra bloco de ressincronizacao para o no e aceita novo inicio de seq")
    p.add_argument("-v", "--verbose", action="store_true")


def apply_common_args(args: argparse.Namespace) -> Config:
    cfg = load_config(args.config)
    if args.port:
        cfg.serial.port = args.port
    if args.baud:
        cfg.serial.baud = args.baud
    if args.allow_resync or args.reset_node is not None:
        cfg.allow_resync = True
    return cfg


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Ponte serial receptor LoRa -> gateway")
    add_common_args(p)
    args = p.parse_args(argv)
    cfg = apply_common_args(args)
    setup_logging(cfg, args.verbose)
    gw = build_gateway(cfg, args.db)
    if args.reset_node is not None:
        b = gw.reset_node(args.reset_node)
        log.warning("no %d ressincronizado (bloco %d)", args.reset_node, b.idx)
    bridge = SerialBridge(gw)
    stop = threading.Event()
    if args.simulate:
        sim = SimulatedReceiver(make_sim_node(cfg, gw), cfg.sim.interval_s, cfg.sim.seed)
        source = sim.lines(bridge.stats, stop)
    else:
        source = serial_lines(cfg.serial.port, cfg.serial.baud, bridge.stats, stop,
                              cfg.serial.reconnect_s)
    try:
        bridge.run(source, stop)
    except KeyboardInterrupt:
        stop.set()
        log.info("encerrado")


if __name__ == "__main__":
    main()
