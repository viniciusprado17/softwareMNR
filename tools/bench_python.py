"""Tarefa A8: mede no Python o tempo de verificacao (gateway) e de assinatura, e o custo do
gateway completo por pacote. Gera CSV com as amostras e imprime o resumo.

Rodar: python tools/bench_python.py [-n 1000]
Saida: reports/bench_python_<data>.csv e reports/bench_python_<data>_resumo.csv

Atencao: numeros do PC/Raspberry Pi. O tempo de assinatura que vai para o artigo e o do
ESP32 (linha INFO,bench_sign_us do firmware), nao este.
"""
import argparse
import csv
import os
import platform
import statistics
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from coldchain import crypto
from coldchain.gateway import Gateway
from coldchain.ledger import Ledger
from coldchain.node_sim import SimNode
from coldchain.packet import split_packet


def summary(name: str, xs: list[float]) -> dict:
    return {
        "medida": name,
        "n": len(xs),
        "media_ms": round(statistics.mean(xs), 4),
        "min_ms": round(min(xs), 4),
        "max_ms": round(max(xs), 4),
        "desvio_ms": round(statistics.stdev(xs), 4) if len(xs) > 1 else 0.0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-n", type=int, default=1000)
    p.add_argument("--out", default=os.path.join(ROOT, "reports"))
    args = p.parse_args()

    key = crypto.generate_keypair()
    pub = key.public_key()
    node = SimNode(1, key, seed=42)
    packets = [node.make_packet(node.random_temp(), ts=1_800_000_000 + i) for i in range(args.n)]

    sign, verify, gateway = [], [], []
    for pkt in packets:
        payload, _ = split_packet(pkt)
        t0 = time.perf_counter()
        sig = crypto.sign(key, payload)
        sign.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        crypto.verify(pub, payload, sig)
        verify.append((time.perf_counter() - t0) * 1000)

    gw = Gateway(Ledger(), {1: pub})
    for pkt in packets:
        t0 = time.perf_counter()
        gw.receive(pkt)
        gateway.append((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    check = gw.ledger.verify_chain(gw.keys)
    chain_ms = (time.perf_counter() - t0) * 1000

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(args.out, exist_ok=True)
    samples = os.path.join(args.out, f"bench_python_{stamp}.csv")
    with open(samples, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i", "assinatura_ms", "verificacao_ms", "gateway_receive_ms"])
        for i, row in enumerate(zip(sign, verify, gateway)):
            w.writerow([i, *(f"{x:.4f}" for x in row)])
    rows = [summary("assinatura", sign), summary("verificacao", verify),
            summary("gateway_receive", gateway)]
    resumo = os.path.join(args.out, f"bench_python_{stamp}_resumo.csv")
    with open(resumo, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) + ["maquina", "python"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "maquina": platform.machine() + " " + platform.processor(),
                        "python": platform.python_version()})

    print(f"maquina: {platform.platform()} | python {platform.python_version()}")
    for r in rows:
        print(f"  {r['medida']:16s} n={r['n']} media={r['media_ms']:.3f} ms "
              f"min={r['min_ms']:.3f} max={r['max_ms']:.3f} desvio={r['desvio_ms']:.3f}")
    print(f"  verify_chain     {len(packets)} blocos em {chain_ms:.1f} ms (ok={check.ok})")
    print(f"amostras: {samples}\nresumo:   {resumo}")


if __name__ == "__main__":
    main()
