"""Demonstracao ponta a ponta sem hardware: no simulado -> gateway -> ledger.

Rodar: python run_demo.py
Mostra: leituras aceitas, adulteracao rejeitada, replay rejeitado e violacao da cadeia detectada.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from coldchain import crypto
from coldchain.gateway import Gateway, Result
from coldchain.ledger import Ledger
from coldchain.node_sim import SimNode
from coldchain.packet import STATUS_NAMES, Reading, split_packet


def main() -> None:
    key = crypto.generate_keypair()
    node = SimNode(node_id=1, private_key=key, seed=42)
    ledger = Ledger()
    gw = Gateway(ledger, {1: key.public_key()})
    t0 = int(time.time())

    print("== 1. Leituras normais e alarme ==")
    temps = [5.1, 4.8, 7.8, 8.6, 5.0]
    last_pkt = b""
    for i, t in enumerate(temps):
        pkt = node.make_packet(t, ts=t0 + i * 10, lat=-10.9472, lon=-37.0731)
        out = gw.receive(pkt)
        r = out.reading
        print(f"  seq={r.seq} T={r.temp_c:5.2f}C {STATUS_NAMES[r.status]:7s} -> {out.result.value}")
        last_pkt = pkt

    print("\n== 2. Adulteracao: alterar temperatura de 8.6 para 5.0 no pacote ==")
    pkt = node.make_packet(8.6, ts=t0 + 60)
    payload, sig = split_packet(pkt)
    fake = Reading.from_payload(payload)
    forged = Reading(**{**fake.__dict__, "temp_c": 5.0, "status": 0}).to_payload() + sig
    print("  resultado:", gw.receive(forged).result.value)

    print("\n== 3. Replay: reenviar um pacote ja aceito ==")
    print("  resultado:", gw.receive(last_pkt).result.value)

    print("\n== 4. No desconhecido ==")
    intruder = SimNode(node_id=99, private_key=crypto.generate_keypair())
    print("  resultado:", gw.receive(intruder.make_packet(5.0)).result.value)

    print("\n== 5. Integridade do ledger ==")
    ok, bad = ledger.verify_chain()
    print(f"  blocos={len(ledger.blocks())} cadeia_ok={ok}")
    ledger.db.execute("UPDATE blocks SET payload = ? WHERE idx = 2", (b"\x00" * 24,))
    ok, bad = ledger.verify_chain()
    print(f"  apos adulterar bloco 2 no banco: cadeia_ok={ok}, primeiro invalido=bloco {bad}")

    print("\n== Tamanho do pacote:", len(last_pkt), "bytes (limite LoRa: 255) ==")


if __name__ == "__main__":
    main()
