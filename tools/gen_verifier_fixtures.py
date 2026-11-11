"""Gera tests/fixtures/verifier_cases.json: cadeias exportadas + o veredito do Python.

O teste tests/js/verifier.test.mjs exige que o verificador do navegador
(static/verifier-core.js) de exatamente o mesmo veredito que Ledger.verify_chain.
As assinaturas ECDSA do Python nao sao deterministicas: o arquivo muda a cada geracao
(os vereditos nao). Rodar: python tools/gen_verifier_fixtures.py
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from coldchain import crypto  # noqa: E402
from coldchain.export import export_chain  # noqa: E402
from coldchain.ledger import Ledger  # noqa: E402
from coldchain.node_sim import SimNode  # noqa: E402
from coldchain.packet import split_packet  # noqa: E402

OUT = os.path.join(ROOT, "tests", "fixtures", "verifier_cases.json")
TS = 1800000000


def build(n=5, resync_after=None):
    key = crypto.generate_keypair()
    node = SimNode(1, key, seed=7)
    ledger = Ledger()
    for i in range(n):
        payload, sig = split_packet(node.make_packet(4.5 + i * 0.25, ts=TS + i * 10))
        ledger.append(1, node.seq, payload, sig, rx_ts=TS + i * 10)
        if resync_after == i + 1:
            ledger.append_resync(1, rx_ts=TS + i * 10 + 1)
    return ledger, {1: key.public_key()}


def sql(ledger, query, args):
    ledger.db.execute(query, args)
    ledger.db.commit()


def rechain(ledger, start):
    """O atacante refaz os hashes a partir de `start` (so a assinatura denuncia)."""
    blocks = ledger.blocks()
    prev = blocks[start - 2].hash if start > 1 else bytes(32)
    for b in blocks[start - 1:]:
        h = hashlib.sha256(prev + b.payload + b.sig).digest()
        sql(ledger, "UPDATE blocks SET prev_hash=?, hash=? WHERE idx=?", (prev, h, b.idx))
        prev = h


def flip(data: bytes, pos: int) -> bytes:
    out = bytearray(data)
    out[pos] ^= 1
    return bytes(out)


def case(name, ledger, keys):
    check = ledger.verify_chain(keys)
    return {"name": name, "doc": export_chain(ledger, keys),
            "expected": {"ok": check.ok, "bad_idx": check.bad_idx, "reason": check.reason}}


def main():
    cases = []
    ledger, keys = build()
    cases.append(case("cadeia valida", ledger, keys))

    ledger, keys = build()
    b = ledger.blocks()[2]
    sql(ledger, "UPDATE blocks SET payload=? WHERE idx=?", (flip(b.payload, 12), b.idx))
    cases.append(case("payload alterado", ledger, keys))

    ledger, keys = build()
    b = ledger.blocks()[2]
    sql(ledger, "UPDATE blocks SET prev_hash=? WHERE idx=?", (flip(b.prev_hash, 0), b.idx))
    cases.append(case("prev_hash alterado", ledger, keys))

    ledger, keys = build()
    b = ledger.blocks()[2]
    sql(ledger, "UPDATE blocks SET hash=? WHERE idx=?", (flip(b.hash, 0), b.idx))
    cases.append(case("hash alterado", ledger, keys))

    ledger, keys = build()
    b = ledger.blocks()[2]
    sql(ledger, "UPDATE blocks SET sig=? WHERE idx=?", (flip(b.sig, 5), b.idx))
    rechain(ledger, 3)
    cases.append(case("assinatura alterada com hashes refeitos", ledger, keys))

    ledger, keys = build()
    b = ledger.blocks()[2]
    sql(ledger, "UPDATE blocks SET payload=? WHERE idx=?", (flip(b.payload, 12), b.idx))
    rechain(ledger, 3)
    cases.append(case("payload alterado com hashes refeitos", ledger, keys))

    ledger, keys = build()
    cases.append(case("no sem chave publica", ledger, {}))

    ledger, keys = build(resync_after=3)
    cases.append(case("resync valido", ledger, keys))

    ledger, keys = build(resync_after=3)
    sql(ledger, "UPDATE blocks SET seq=5 WHERE kind='resync'", ())
    cases.append(case("resync adulterado", ledger, keys))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"aviso": "Gerado por tools/gen_verifier_fixtures.py. Chaves de teste.", "cases": cases}, f, indent=1)
    for c in cases:
        print(f"{c['name']:42s} -> {c['expected']}")


if __name__ == "__main__":
    main()
