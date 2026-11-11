"""Bateria "do artigo" ao vivo: testes 1 e 2 da simulacao do artigo (Tabela 2).

Roda num gateway DESCARTAVEL (ledger em memoria, chave de teste gerada na hora): nao toca
na corrente nem nos eventos reais. O teste 3 do artigo (latencia) nao e repetido aqui:
latencia se mede no ESP32 (docs/MEDICOES.md).
"""
from __future__ import annotations

import random
import struct

from . import crypto
from .decision import Thresholds, classify
from .gateway import Gateway, Result
from .ledger import Ledger
from .packet import STATUS_ALARM, Reading

NOTE = ("Mesmos testes da simulação do artigo (Tabela 2), executados agora neste computador "
        "com chave de teste. A latência do artigo não é medida aqui.")
TEMP_OFFSET = 11  # campo temp no payload (">BHIIhHBii": 1+2+4+4)


def classification_test(th: Thresholds = Thresholds()) -> dict:
    """Teste 1: 14 temperaturas de 2 a 15 C, limiar 8 C (alerta do artigo = ALARME)."""
    temps = list(range(2, 16))
    correct = sum((classify(float(t), th) == STATUS_ALARM) == (t > th.high) for t in temps)
    return {"total": len(temps), "correct": correct}


def tamper_test(n: int = 50, seed: int = 42) -> dict:
    """Teste 2: n pacotes assinados com a temperatura alterada (+10,00 C) depois de assinar.

    Controle: o pacote original de cada rodada tambem e enviado e precisa ser ACEITO,
    para provar que o gateway nao esta simplesmente recusando tudo.
    """
    rng = random.Random(seed)
    key = crypto.generate_keypair()
    gw = Gateway(Ledger(":memory:"), {1: key.public_key()})
    rejected = genuine_ok = 0
    for i in range(n):
        r = Reading(1, i + 1, 1_800_000_000 + i, round(rng.uniform(2, 8), 2), 40.0, 0, None, None)
        payload = r.to_payload()
        sig = crypto.sign(key, payload)
        forged = bytearray(payload)
        temp = struct.unpack_from(">h", forged, TEMP_OFFSET)[0]
        struct.pack_into(">h", forged, TEMP_OFFSET, temp + 1000)
        if gw.receive(bytes(forged) + sig).result != Result.ACCEPTED:
            rejected += 1
        if gw.receive(payload + sig).result == Result.ACCEPTED:
            genuine_ok += 1
    gw.ledger.close()
    return {"total": n, "rejected": rejected, "accepted": n - rejected,
            "genuine_total": n, "genuine_accepted": genuine_ok}


def run_battery(th: Thresholds = Thresholds()) -> dict:
    return {"classification": classification_test(th), "tamper": tamper_test(), "note": NOTE}
