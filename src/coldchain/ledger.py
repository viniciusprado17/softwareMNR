"""Ledger SQLite com cadeia de hash: hash_i = SHA256(hash_{i-1} || payload || sig)."""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass

GENESIS = b"\x00" * 32


@dataclass(frozen=True)
class Block:
    idx: int
    node_id: int
    seq: int
    payload: bytes
    sig: bytes
    prev_hash: bytes
    hash: bytes


def _hash(prev: bytes, payload: bytes, sig: bytes) -> bytes:
    return hashlib.sha256(prev + payload + sig).digest()


class Ledger:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS blocks (
                idx INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                payload BLOB NOT NULL,
                sig BLOB NOT NULL,
                prev_hash BLOB NOT NULL,
                hash BLOB NOT NULL)"""
        )
        self.db.commit()

    def last_hash(self) -> bytes:
        row = self.db.execute("SELECT hash FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS

    def last_seq(self, node_id: int) -> int | None:
        row = self.db.execute(
            "SELECT MAX(seq) FROM blocks WHERE node_id=?", (node_id,)
        ).fetchone()
        return row[0]

    def append(self, node_id: int, seq: int, payload: bytes, sig: bytes) -> Block:
        prev = self.last_hash()
        h = _hash(prev, payload, sig)
        cur = self.db.execute(
            "INSERT INTO blocks (node_id, seq, payload, sig, prev_hash, hash) VALUES (?,?,?,?,?,?)",
            (node_id, seq, payload, sig, prev, h),
        )
        self.db.commit()
        return Block(cur.lastrowid, node_id, seq, payload, sig, prev, h)

    def blocks(self) -> list[Block]:
        rows = self.db.execute(
            "SELECT idx,node_id,seq,payload,sig,prev_hash,hash FROM blocks ORDER BY idx"
        ).fetchall()
        return [Block(*r) for r in rows]

    def verify_chain(self) -> tuple[bool, int | None]:
        """Retorna (ok, indice_do_primeiro_bloco_invalido)."""
        prev = GENESIS
        for b in self.blocks():
            if b.prev_hash != prev or b.hash != _hash(prev, b.payload, b.sig):
                return False, b.idx
            prev = b.hash
        return True, None
