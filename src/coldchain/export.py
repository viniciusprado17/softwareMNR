"""Export da corrente para conferencia independente (verificador no navegador, laudo).

Tudo em hex minusculo. O verificador refaz hash e assinatura so com este documento.
"""
from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import ec

from . import crypto
from .ledger import GENESIS, Ledger

EXPORT_FORMAT = "coldchain-export/1"


def export_chain(ledger: Ledger, keys: dict[int, ec.EllipticCurvePublicKey]) -> dict:
    blocks = ledger.blocks()
    return {
        "format": EXPORT_FORMAT,
        "curve": "P-256",
        "genesis": GENESIS.hex(),
        "nodes": {str(n): crypto.public_bytes_raw(k).hex() for n, k in sorted(keys.items())},
        "head": (blocks[-1].hash if blocks else GENESIS).hex(),
        "blocks": [
            {
                "idx": b.idx,
                "kind": b.kind,
                "node_id": b.node_id,
                "seq": b.seq,
                "rx_ts": b.rx_ts,
                "prev_hash": b.prev_hash.hex(),
                "payload": b.payload.hex(),
                "sig": b.sig.hex(),
                "hash": b.hash.hex(),
            }
            for b in blocks
        ],
    }
