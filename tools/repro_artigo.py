"""Reproduz os 3 testes da simulacao do artigo (Secao 3.3 e Tabela 2) com o codigo do projeto.

Teste 1: 14 temperaturas de 2 a 15 C, limiar 8 C (alerta = status ALARME).
Teste 2: 50 adulteracoes do campo de temperatura apos assinar; todas devem ser detectadas.
Teste 3: latencia de gerar e assinar um pacote, n=100 (media, minimo, maximo).

Diferenca declarada: o artigo usou secp256k1 em Python; aqui usa-se a curva de coldchain.crypto.
Rodar: python tools/repro_artigo.py
"""
import os
import random
import statistics
import struct
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from coldchain import crypto
from coldchain.decision import classify
from coldchain.packet import STATUS_ALARM, Reading, split_packet


def teste1() -> tuple[int, int]:
    temps = list(range(2, 16))  # 14 valores
    ok = sum((classify(float(t)) == STATUS_ALARM) == (t > 8) for t in temps)
    return ok, len(temps)


def teste2(priv, pub) -> tuple[int, int]:
    rng = random.Random(42)
    detectados = 0
    for i in range(50):
        r = Reading(1, i + 1, 1_800_000_000 + i, rng.uniform(2, 8), 40.0, 0, None, None)
        payload = r.to_payload()
        sig = crypto.sign(priv, payload)
        adulterado = bytearray(payload)
        # temp ocupa os bytes 11..12 (">BHIIhHBii": 1+2+4+4 = 11)
        temp = struct.unpack_from(">h", adulterado, 11)[0]
        struct.pack_into(">h", adulterado, 11, temp + 1000)  # +10,00 C
        if not crypto.verify(pub, bytes(adulterado), sig):
            detectados += 1
    return detectados, 50


def teste3(priv) -> tuple[float, float, float]:
    rng = random.Random(42)
    tempos = []
    for i in range(100):
        t0 = time.perf_counter()
        r = Reading(1, i + 1, 1_800_000_000 + i, rng.uniform(2, 8), 40.0, 0, None, None)
        crypto.sign(priv, r.to_payload())
        tempos.append((time.perf_counter() - t0) * 1000)
    return statistics.mean(tempos), min(tempos), max(tempos)


def main() -> None:
    priv = crypto.generate_keypair()
    pub = priv.public_key()
    a, n = teste1()
    print(f"Teste 1 (classificacao termica): {a}/{n}")
    d, n = teste2(priv, pub)
    print(f"Teste 2 (deteccao de adulteracao): {d}/{n}")
    m, lo, hi = teste3(priv)
    print(f"Teste 3 (latencia, n=100): media {m:.2f} ms, min {lo:.2f}, max {hi:.2f}")
    print("Artigo: 14/14, 50/50, 0,59 ms (min 0,51 / max 0,69) em CPU de PC.")


if __name__ == "__main__":
    main()
