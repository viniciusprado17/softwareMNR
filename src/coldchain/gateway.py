"""Gateway: valida pacote recebido e grava no ledger.

Ordem fixa das verificacoes (Secao 10.1): tamanho, payload, no conhecido, assinatura,
replay. Cada rejeicao vira um evento (tabela `events`) e NAO entra na corrente.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum

from cryptography.hazmat.primitives.asymmetric import ec

from . import crypto
from .decision import DEFAULT, Thresholds, classify
from .ledger import Block, Ledger
from .packet import STATUS_NAMES, Reading, split_packet


class Result(str, Enum):
    ACCEPTED = "aceito"
    BAD_LENGTH = "tamanho_invalido"
    BAD_SIGNATURE = "assinatura_invalida"
    UNKNOWN_NODE = "no_desconhecido"
    REPLAY = "replay"
    BAD_PAYLOAD = "payload_invalido"


EVENT_SILENCE = "silencio"
EVENT_RESYNC = "ressincronizacao"
ANOMALY_STATUS = "status_divergente"


@dataclass
class Outcome:
    result: Result
    reading: Reading | None = None
    block: Block | None = None
    anomaly: str | None = None
    rssi: int | None = None
    snr: float | None = None
    rx_ts: int | None = None


class Gateway:
    def __init__(
        self,
        ledger: Ledger,
        trusted_keys: dict[int, ec.EllipticCurvePublicKey],
        thresholds: Thresholds = DEFAULT,
        expected_interval_s: float = 10.0,
        silence_factor: int = 3,
        allow_resync: bool = False,
    ):
        self.ledger = ledger
        self.keys = trusted_keys
        self.th = thresholds
        self.expected_interval_s = expected_interval_s
        self.silence_factor = silence_factor
        self.allow_resync = allow_resync
        self.lock = threading.RLock()
        self.started_at = time.time()
        self.last_rx: dict[int, float] = {}  # node_id -> hora do ultimo pacote aceito
        self._silent: set[int] = set()  # nos ja sinalizados como em silencio
        self.last_accepted_packet: bytes | None = None

    def receive(
        self,
        packet: bytes,
        rssi: int | None = None,
        snr: float | None = None,
        rx_ts: int | None = None,
    ) -> Outcome:
        rx_ts = int(time.time()) if rx_ts is None else rx_ts
        with self.lock:
            out = self._validate(packet, rssi, snr, rx_ts)
            self._log(out, len(packet))
            return out

    def _validate(self, packet: bytes, rssi, snr, rx_ts: int) -> Outcome:
        def reject(result: Result, reading: Reading | None = None) -> Outcome:
            return Outcome(result, reading, rssi=rssi, snr=snr, rx_ts=rx_ts)

        try:
            payload, sig = split_packet(packet)
        except ValueError:
            return reject(Result.BAD_LENGTH)
        try:
            reading = Reading.from_payload(payload)
        except ValueError:
            return reject(Result.BAD_PAYLOAD)
        key = self.keys.get(reading.node_id)
        if key is None:
            return reject(Result.UNKNOWN_NODE, reading)
        if not crypto.verify(key, payload, sig):
            return reject(Result.BAD_SIGNATURE, reading)
        last = self.ledger.last_seq(reading.node_id)
        if last is not None and reading.seq <= last:
            return reject(Result.REPLAY, reading)
        # O no nao e a unica fonte da verdade: o gateway recalcula o status.
        anomaly = None
        if classify(reading.temp_c, self.th) != reading.status:
            anomaly = ANOMALY_STATUS
        block = self.ledger.append(
            reading.node_id, reading.seq, payload, sig,
            rx_ts=rx_ts, rssi=rssi, snr=snr, anomaly=anomaly,
        )
        self.last_rx[reading.node_id] = time.time()
        self._silent.discard(reading.node_id)
        self.last_accepted_packet = packet
        return Outcome(Result.ACCEPTED, reading, block, anomaly, rssi, snr, rx_ts)

    def _log(self, out: Outcome, length: int) -> None:
        r = out.reading
        parts = []
        if r is not None:
            parts.append(
                f"seq={r.seq} T={r.temp_c:.2f}C {STATUS_NAMES.get(r.status, '?')}"
            )
        else:
            parts.append(f"len={length}")
        if out.rssi is not None:
            parts.append(f"rssi={out.rssi} snr={out.snr}")
        if out.anomaly:
            parts.append(f"anomalia={out.anomaly}")
        if out.block is not None:
            parts.append(f"bloco={out.block.idx}")
        self.ledger.add_event(
            out.result.value, " ".join(parts), r.node_id if r else None, out.rx_ts
        )

    def check_silence(self, now: float | None = None) -> list[int]:
        """Gera evento `silencio` para cada no cadastrado sem pacote por N intervalos.

        Cada periodo de silencio gera um unico evento; o no sai do silencio ao mandar um
        pacote aceito. Devolve os nos sinalizados nesta chamada.
        """
        now = time.time() if now is None else now
        limit = self.expected_interval_s * self.silence_factor
        flagged = []
        with self.lock:
            for node_id in self.keys:
                since = self.last_rx.get(node_id, self.started_at)
                if node_id not in self._silent and now - since > limit:
                    self._silent.add(node_id)
                    flagged.append(node_id)
                    self.ledger.add_event(
                        EVENT_SILENCE, f"sem pacotes ha {now - since:.0f} s", node_id, int(now)
                    )
        return flagged

    def reset_node(self, node_id: int) -> Block:
        """Aceita um novo inicio de seq para o no. So com allow_resync (--reset-node)."""
        if not self.allow_resync:
            raise PermissionError("ressincronizacao desligada (use --allow-resync)")
        with self.lock:
            block = self.ledger.append_resync(node_id)
            self.ledger.add_event(EVENT_RESYNC, f"bloco={block.idx}", node_id)
            return block

    def reset_state(self) -> None:
        """Restaurar demo: zera ledger e contadores."""
        with self.lock:
            self.ledger.reset()
            self.last_rx.clear()
            self._silent.clear()
            self.last_accepted_packet = None
            self.started_at = time.time()
