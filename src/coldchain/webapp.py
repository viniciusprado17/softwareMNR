"""Tela de demonstracao (FastAPI + pagina local, sem CDN) e API HTTP (Secao 10.5).

Uso:
  python -m coldchain.webapp --simulate --demo-controls     # ensaio sem hardware
  python -m coldchain.webapp --port /dev/ttyUSB0 --demo-controls
Abrir http://127.0.0.1:8000

Os botoes de ataque so existem com --demo-controls.
"""
from __future__ import annotations

import argparse
import base64
import logging
import os
import secrets
import socket
import struct
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Config
from .export import export_chain
from .gateway import Gateway, Outcome
from .battery import run_battery
from .ledger import CHAIN_BROKEN_HASH, CHAIN_PREV_MISMATCH, KIND_DATA, Block
from .packet import PAYLOAD_LEN, STATUS_NAMES, STATUS_OK, Reading, split_packet
from .serial_bridge import (
    SerialBridge,
    SimulatedReceiver,
    add_common_args,
    apply_common_args,
    build_gateway,
    make_sim_node,
    serial_lines,
    setup_logging,
)

log = logging.getLogger("coldchain.web")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TEMP_OFFSET = 11  # offset do campo temp no payload (">BHIIhHBii": 1+2+4+4)
DEMO_FORGED_TEMP = 5.0  # roteiro da demonstracao: 8,6 C vira 5,0 C


def lan_addresses() -> list[str]:
    """Enderecos IPv4 deste computador na rede local (sem loopback nem link-local).

    O primeiro e o da rota padrao (o mais provavel de ser o Wi-Fi); nao envia nenhum pacote.
    """
    found: list[str] = []

    def add(ip: str) -> None:
        if ip and not ip.startswith(("127.", "169.254.", "0.")) and ip not in found:
            found.append(ip)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # UDP: so escolhe a interface, nao transmite
            add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            add(ip)
    except OSError:
        pass
    return found


class HeatRequest(BaseModel):
    on: bool


def _block_json(b: Block) -> dict:
    r = Reading.from_payload(b.payload)
    return {
        "idx": b.idx,
        "node_id": b.node_id,
        "seq": b.seq,
        "ts": r.ts,
        "rx_ts": b.rx_ts,
        "temp_c": b.temp_c,
        "hum_pct": r.hum_pct,
        "status": b.status,
        "status_name": STATUS_NAMES.get(b.status, "?"),
        "lat": r.lat,
        "lon": r.lon,
        "rssi": b.rssi,
        "snr": b.snr,
        "anomaly": b.anomaly,
        "hash": b.hash.hex(),
    }


def _outcome_json(out: Outcome) -> dict:
    r = out.reading
    return {
        "result": out.result.value,
        "node_id": r.node_id if r else None,
        "seq": r.seq if r else None,
        "temp_c": r.temp_c if r else None,
        "block": out.block.idx if out.block else None,
    }


def _with_temp(payload: bytes, temp_c: float) -> bytes:
    p = bytearray(payload)
    struct.pack_into(">h", p, TEMP_OFFSET, round(temp_c * 100))
    return bytes(p)


def create_app(
    cfg: Config,
    gateway: Gateway,
    simulate: bool = False,
    demo_controls: bool = False,
    start_bridge: bool = True,
    password: str | None = None,
) -> FastAPI:
    bridge = SerialBridge(gateway)
    stop = threading.Event()
    sim = (
        SimulatedReceiver(make_sim_node(cfg, gateway), cfg.sim.interval_s, cfg.sim.seed)
        if simulate
        else None
    )

    def run_bridge() -> None:
        if sim is not None:
            source = sim.lines(bridge.stats, stop)
        else:
            source = serial_lines(cfg.serial.port, cfg.serial.baud, bridge.stats, stop,
                                  cfg.serial.reconnect_s)
        bridge.run(source, stop)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        thread = None
        if start_bridge:
            thread = threading.Thread(target=run_bridge, name="bridge", daemon=True)
            thread.start()
        yield
        stop.set()
        if thread:
            thread.join(timeout=3)

    app = FastAPI(title="MNR 2026 Cadeia de Frio", lifespan=lifespan)
    app.state.gateway = gateway
    app.state.bridge = bridge
    app.state.sim = sim

    if password:
        # Senha simples (HTTP Basic, qualquer usuario) para o link publico da equipe.
        @app.middleware("http")
        async def require_password(request: Request, call_next):
            if request.url.path == "/healthz":
                return await call_next(request)
            given = ""
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("basic "):
                try:
                    given = base64.b64decode(auth[6:]).decode("utf-8").partition(":")[2]
                except (ValueError, UnicodeDecodeError):
                    given = ""
            if not secrets.compare_digest(given.encode(), password.encode()):
                return Response("Senha necessaria", status_code=401,
                                headers={"WWW-Authenticate": 'Basic realm="Cadeia de Frio MNR 2026"'})
            return await call_next(request)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"ok": True}

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/laudo", include_in_schema=False)
    def report_page():
        return FileResponse(os.path.join(STATIC_DIR, "laudo.html"))

    @app.get("/verificador", include_in_schema=False)
    def verifier_page():
        return FileResponse(os.path.join(STATIC_DIR, "verificador.html"))

    # App instalavel no celular (PWA): manifesto e service worker precisam estar na raiz.
    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return FileResponse(os.path.join(STATIC_DIR, "manifest.webmanifest"),
                            media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript",
                            headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/api/access")
    def access():
        """Enderecos para abrir a tela em outro aparelho (usado pelo QR code)."""
        host, port = cfg.web.host, cfg.web.port
        if host in ("0.0.0.0", "::", ""):
            addrs = lan_addresses()
        elif host.startswith("127.") or host in ("localhost", "::1"):
            addrs = []
        else:
            addrs = [host]
        return {
            "host": host,
            "port": port,
            "lan_open": bool(addrs),
            "urls": [f"http://{ip}:{port}" for ip in addrs],
            "password_required": bool(password),
        }

    @app.get("/api/status")
    def status():
        gateway.check_silence()
        now = time.time()
        head = gateway.ledger.last_hash().hex()
        s = bridge.stats
        nodes = []
        for node_id in sorted(gateway.keys):
            seen = gateway.last_rx.get(node_id)
            nodes.append({
                "node_id": node_id,
                "last_seq": gateway.ledger.last_seq(node_id),
                "seconds_since_last": None if seen is None else round(now - seen, 1),
                "silent": node_id in gateway._silent,
            })
        return {
            "serial": {
                "connected": s.connected,
                "source": s.source,
                "lines": s.lines,
                "rx": s.rx,
                "ignored": s.ignored,
                "errors": s.errors,
                "last_info": s.last_info,
            },
            "simulate": sim is not None,
            "heating": sim.heating if sim else False,
            "demo_controls": demo_controls,
            "nodes": nodes,
            "chain": {"blocks": gateway.ledger.count(), "head": head},
            "event_counts": gateway.ledger.event_counts(),
            "thresholds": gateway.th.__dict__,
            "expected_interval_s": gateway.expected_interval_s,
        }

    @app.get("/api/readings")
    def readings(limit: int = 100):
        blocks = gateway.ledger.blocks(limit=max(1, min(limit, 2000)), kind=KIND_DATA)
        return [_block_json(b) for b in blocks]

    @app.get("/api/events")
    def events(limit: int = 100):
        return [e.__dict__ for e in gateway.ledger.events(max(1, min(limit, 2000)))]

    @app.get("/api/export/chain")
    def export(download: int = 0):
        """Corrente inteira para conferencia independente (verificador no navegador)."""
        doc = export_chain(gateway.ledger, gateway.keys)
        if not download:
            return doc
        name = time.strftime("corrente_%Y-%m-%d_%H-%M-%S.json")
        return JSONResponse(doc, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.get("/api/chain/verify")
    def chain_verify():
        check = gateway.ledger.verify_chain(gateway.keys)
        out = {"ok": check.ok, "bloco_invalido": check.bad_idx, "motivo": check.reason}
        # Prova visivel da quebra (campos opcionais, so quando ha divergencia de hash/elo)
        if check.reason in (CHAIN_BROKEN_HASH, CHAIN_PREV_MISMATCH):
            proof = gateway.ledger.explain_failure(check.bad_idx)
            keys = (("hash_gravado", "hash_recalculado") if check.reason == CHAIN_BROKEN_HASH
                    else ("prev_gravado", "prev_esperado"))
            out.update({k: proof[k] for k in keys if k in proof})
        return out

    if sim is not None:
        @app.post("/api/sim/heat")
        def sim_heat(req: HeatRequest):
            sim.heat(req.on)
            return {"heating": sim.heating}

    if demo_controls:
        def last_packet() -> bytes:
            pkt = gateway.last_accepted_packet
            if pkt is None:
                raise HTTPException(409, "nenhum pacote aceito ainda")
            return pkt

        @app.post("/api/demo/tamper")
        def demo_tamper():
            payload, sig = split_packet(last_packet())
            original = Reading.from_payload(payload)
            forged_temp = DEMO_FORGED_TEMP
            if abs(original.temp_c - forged_temp) < 0.01:
                forged_temp = 9.0
            forged = _with_temp(payload, forged_temp)
            out = gateway.receive(forged + sig)
            return {**_outcome_json(out), "original_temp": original.temp_c,
                    "forged_temp": forged_temp}

        @app.post("/api/demo/replay")
        def demo_replay():
            return _outcome_json(gateway.receive(last_packet()))

        @app.post("/api/demo/corrupt-db")
        def demo_corrupt_db():
            data = gateway.ledger.blocks(kind=KIND_DATA)
            if len(data) < 2:
                raise HTTPException(409, "sao necessarios pelo menos 2 blocos")
            # Fraude tipica: "limpar" um ALARME antigo. Sem alarme, edita um bloco do meio.
            older = data[:-1]
            alarms = [b for b in older if b.status != STATUS_OK]
            target = alarms[-1] if alarms else older[len(older) // 2]
            new_payload = _with_temp(target.payload, DEMO_FORGED_TEMP)
            new_payload = new_payload[:15] + bytes([STATUS_OK]) + new_payload[16:]
            assert len(new_payload) == PAYLOAD_LEN
            with gateway.ledger.lock:
                gateway.ledger.db.execute(
                    "UPDATE blocks SET payload=?, temp_c=?, status=? WHERE idx=?",
                    (new_payload, DEMO_FORGED_TEMP, STATUS_OK, target.idx),
                )
                gateway.ledger.db.commit()
            gateway.ledger.add_event("demo_banco_adulterado",
                                     f"bloco={target.idx} {target.temp_c:.2f}C -> "
                                     f"{DEMO_FORGED_TEMP:.2f}C", target.node_id)
            return {"idx": target.idx, "from_temp": target.temp_c, "to_temp": DEMO_FORGED_TEMP}

        @app.post("/api/demo/battery")
        def demo_battery():
            # Gateway descartavel: a corrente e os eventos reais nao mudam.
            return run_battery(gateway.th)

        @app.post("/api/demo/reset")
        def demo_reset():
            gateway.reset_state()
            if sim is not None:
                sim.heat(False)
            return {"ok": True}

    return app


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Tela de demonstracao do gateway")
    add_common_args(p)
    p.add_argument("--demo-controls", action="store_true", help="habilita os botoes de ataque")
    p.add_argument("--host")
    p.add_argument("--web-port", type=int)
    p.add_argument("--password", default=os.environ.get("CC_PASSWORD") or None,
                   help="exige senha na tela (padrao: variavel CC_PASSWORD)")
    args = p.parse_args(argv)
    cfg = apply_common_args(args)
    if args.host:
        cfg.web.host = args.host
    if args.web_port:
        cfg.web.port = args.web_port
    elif os.environ.get("PORT"):  # hospedagem (Render, Railway...) define a porta
        cfg.web.port = int(os.environ["PORT"])
    setup_logging(cfg, args.verbose)
    gw = build_gateway(cfg, args.db)
    if args.reset_node is not None:
        gw.reset_node(args.reset_node)
    app = create_app(cfg, gw, simulate=args.simulate, demo_controls=args.demo_controls,
                     password=args.password)

    import uvicorn

    log.info("tela em http://%s:%d", cfg.web.host, cfg.web.port)
    uvicorn.run(app, host=cfg.web.host, port=cfg.web.port, log_level="warning")


if __name__ == "__main__":
    main()
