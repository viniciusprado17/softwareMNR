"""Gera tests/vectors.json: vetores dourados para interoperabilidade firmware <-> Python.

A chave daqui e SOMENTE de teste e fica publica no repositorio. Nunca usar na demonstracao.
Rodar: python tools/gen_vectors.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cryptography.hazmat.primitives.asymmetric import ec

from coldchain import crypto
from coldchain.packet import Reading

# Chave de teste fixa (escalar privado de 32 bytes), para o vetor ser reproduzivel.
PRIV_HEX = "1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020101"


def main() -> None:
    priv = ec.derive_private_key(int(PRIV_HEX, 16), crypto.CURVE)
    pub = crypto.public_bytes_raw(priv.public_key())

    cases = [
        Reading(1, 1, 1_800_000_000, 5.25, 43.50, 0, -10.9472, -37.0731),
        Reading(1, 2, 1_800_000_010, 7.80, 40.00, 1, None, None),
        Reading(1, 3, 1_800_000_020, 8.60, 38.25, 2, None, None),
        Reading(1, 4, 0, -3.50, 90.00, 2, None, None),
    ]
    vectors = []
    for r in cases:
        payload = r.to_payload()
        sig = crypto.sign(priv, payload)
        vectors.append(
            {
                "reading": {
                    "node_id": r.node_id, "seq": r.seq, "ts": r.ts,
                    "temp_c": r.temp_c, "hum_pct": r.hum_pct, "status": r.status,
                    "lat": r.lat, "lon": r.lon,
                },
                "payload_hex": payload.hex(),
                "sig_hex": sig.hex(),
                "packet_hex": (payload + sig).hex(),
                "expect": "valid",
            }
        )

    base = vectors[0]
    p = bytearray.fromhex(base["payload_hex"])
    p[13] ^= 0x01
    vectors.append({"note": "1 bit alterado no payload", "payload_hex": p.hex(),
                    "sig_hex": base["sig_hex"], "packet_hex": p.hex() + base["sig_hex"],
                    "expect": "invalid"})
    s = bytearray.fromhex(base["sig_hex"])
    s[-1] ^= 0x01
    vectors.append({"note": "1 bit alterado na assinatura", "payload_hex": base["payload_hex"],
                    "sig_hex": s.hex(), "packet_hex": base["payload_hex"] + s.hex(),
                    "expect": "invalid"})

    out = {
        "aviso": "Chave publica de teste. Nao usar em producao nem na demonstracao.",
        "curve": "secp256r1",
        "private_key_hex": PRIV_HEX,
        "public_key_hex": pub.hex(),
        "vectors": vectors,
    }
    path = os.path.join(ROOT, "tests", "vectors.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print("gerado:", path, f"({len(vectors)} vetores)")


if __name__ == "__main__":
    main()
