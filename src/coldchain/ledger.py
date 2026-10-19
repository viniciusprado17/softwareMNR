"""Ledger SQLite com cadeia de hash: hash_i = SHA256(hash_{i-1} || payload || sig).

As colunas rx_ts, rssi, snr, temp_c, status e anomaly sao conveniencia para consulta e NAO
entram no hash. A fonte da verdade e payload + sig; por isso verify_chain reconfere a
assinatura de cada bloco e compara as colunas decodificadas com o payload.

Rejeicoes (assinatura invalida, replay, no desconhecido...) vao para a tabela `events`,
fora da corrente: a corrente so contem dados validos.
"""
from __future__ import annotations

import hashlib
import sqlite3
import struct
import threading
import time
from dataclasses import dataclass
from typing import NamedTuple

from cryptography.hazmat.primitives.asymmetric import ec

from . import crypto
from .packet import Reading

GENESIS = b"\x00" * 32

KIND_DATA = "data"
KIND_RESYNC = "resync"
# Bloco de ressincronizacao (--reset-node): payload fixo, sem assinatura.
RESYNC_MAGIC = b"RESYNC"
RESYNC_FMT = ">6sHI"  # magic, node_id, rx_ts

# Motivos de falha da corrente (Secao 10.3 da especificacao)
CHAIN_PREV_MISMATCH = "prev_hash_diferente"
CHAIN_BROKEN_HASH = "hash_quebrado"
CHAIN_BAD_SIGNATURE = "assinatura_invalida"
CHAIN_COLUMN_MISMATCH = "coluna_divergente"

_COLUMNS = (
    "idx,node_id,seq,payload,sig,prev_hash,hash,rx_ts,rssi,snr,temp_c,status,anomaly,kind"
)


@dataclass(frozen=True)
class Block:
    idx: int
    node_id: int
    seq: int
    payload: bytes
    sig: bytes
    prev_hash: bytes
    hash: bytes
    rx_ts: int | None = None
    rssi: int | None = None
    snr: float | None = None
    temp_c: float | None = None
    status: int | None = None
    anomaly: str | None = None
    kind: str = KIND_DATA


@dataclass(frozen=True)
class Event:
    id: int
    rx_ts: int
    kind: str
    node_id: int | None
    detail: str


class ChainCheck(NamedTuple):
    ok: bool
    bad_idx: int | None = None
    reason: str | None = None


def _hash(prev: bytes, payload: bytes, sig: bytes) -> bytes:
    return hashlib.sha256(prev + payload + sig).digest()


class Ledger:
    def __init__(self, path: str = ":memory:"):
        # check_same_thread=False: a ponte serial e a tela web rodam em threads diferentes;
        # o acesso e serializado pelo lock.
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        with self.lock:
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
            # Migracao de bancos antigos: acrescenta as colunas de conveniencia.
            have = {r[1] for r in self.db.execute("PRAGMA table_info(blocks)")}
            for name, decl in (
                ("rx_ts", "INTEGER"),
                ("rssi", "INTEGER"),
                ("snr", "REAL"),
                ("temp_c", "REAL"),
                ("status", "INTEGER"),
                ("anomaly", "TEXT"),
                ("kind", f"TEXT NOT NULL DEFAULT '{KIND_DATA}'"),
            ):
                if name not in have:
                    self.db.execute(f"ALTER TABLE blocks ADD COLUMN {name} {decl}")
            self.db.execute(
                """CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rx_ts INTEGER,
                    kind TEXT,
                    node_id INTEGER,
                    detail TEXT)"""
            )
            self.db.commit()

    # ---- corrente ---------------------------------------------------------------------

    def last_hash(self) -> bytes:
        with self.lock:
            row = self.db.execute(
                "SELECT hash FROM blocks ORDER BY idx DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else GENESIS

    def last_seq(self, node_id: int) -> int | None:
        """Maior seq aceito do no, considerando so os blocos apos a ultima ressincronizacao."""
        with self.lock:
            row = self.db.execute(
                """SELECT MAX(seq) FROM blocks WHERE node_id=? AND kind=? AND idx > COALESCE(
                       (SELECT MAX(idx) FROM blocks WHERE node_id=? AND kind=?), 0)""",
                (node_id, KIND_DATA, node_id, KIND_RESYNC),
            ).fetchone()
        return row[0]

    def append(
        self,
        node_id: int,
        seq: int,
        payload: bytes,
        sig: bytes,
        rx_ts: int | None = None,
        rssi: int | None = None,
        snr: float | None = None,
        anomaly: str | None = None,
    ) -> Block:
        reading = Reading.from_payload(payload)
        rx_ts = int(time.time()) if rx_ts is None else rx_ts
        return self._insert(
            Block(
                0, node_id, seq, payload, sig, b"", b"",
                rx_ts, rssi, snr, reading.temp_c, reading.status, anomaly, KIND_DATA,
            )
        )

    def append_resync(self, node_id: int, rx_ts: int | None = None) -> Block:
        """Bloco especial que permite ao no recomecar o seq (plano de emergencia)."""
        rx_ts = int(time.time()) if rx_ts is None else rx_ts
        payload = struct.pack(RESYNC_FMT, RESYNC_MAGIC, node_id, rx_ts)
        return self._insert(
            Block(0, node_id, 0, payload, b"", b"", b"", rx_ts, kind=KIND_RESYNC)
        )

    def _insert(self, b: Block) -> Block:
        with self.lock:
            prev = self.last_hash()
            h = _hash(prev, b.payload, b.sig)
            cur = self.db.execute(
                """INSERT INTO blocks (node_id, seq, payload, sig, prev_hash, hash,
                       rx_ts, rssi, snr, temp_c, status, anomaly, kind)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (b.node_id, b.seq, b.payload, b.sig, prev, h, b.rx_ts, b.rssi, b.snr,
                 b.temp_c, b.status, b.anomaly, b.kind),
            )
            self.db.commit()
            return Block(cur.lastrowid, b.node_id, b.seq, b.payload, b.sig, prev, h,
                         b.rx_ts, b.rssi, b.snr, b.temp_c, b.status, b.anomaly, b.kind)

    def blocks(self, limit: int | None = None, kind: str | None = None) -> list[Block]:
        """Blocos em ordem crescente. Com limit, devolve so os ultimos `limit`."""
        where, args = ("WHERE kind=?", [kind]) if kind else ("", [])
        sql = f"SELECT {_COLUMNS} FROM blocks {where} ORDER BY idx"
        if limit is not None:
            sql = f"SELECT * FROM (SELECT {_COLUMNS} FROM blocks {where} ORDER BY idx DESC LIMIT ?) ORDER BY idx"
            args.append(limit)
        with self.lock:
            rows = self.db.execute(sql, args).fetchall()
        return [Block(*r) for r in rows]

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]

    def verify_chain(
        self, keys: dict[int, ec.EllipticCurvePublicKey] | None = None
    ) -> ChainCheck:
        """Confere a corrente e aponta o primeiro bloco invalido e o motivo.

        Sem `keys`, so a corrente de hash e conferida. Com `keys`, tambem a assinatura de
        cada bloco e as colunas decodificadas.
        """
        prev = GENESIS
        for b in self.blocks():
            if b.prev_hash != prev:
                return ChainCheck(False, b.idx, CHAIN_PREV_MISMATCH)
            if b.hash != _hash(prev, b.payload, b.sig):
                return ChainCheck(False, b.idx, CHAIN_BROKEN_HASH)
            if keys is not None:
                reason = self._check_block(b, keys)
                if reason:
                    return ChainCheck(False, b.idx, reason)
            prev = b.hash
        return ChainCheck(True)

    @staticmethod
    def _check_block(b: Block, keys: dict[int, ec.EllipticCurvePublicKey]) -> str | None:
        if b.kind == KIND_RESYNC:
            try:
                magic, node_id, _ = struct.unpack(RESYNC_FMT, b.payload)
            except struct.error:
                return CHAIN_COLUMN_MISMATCH
            ok = magic == RESYNC_MAGIC and node_id == b.node_id and b.sig == b"" and b.seq == 0
            return None if ok else CHAIN_COLUMN_MISMATCH
        if b.kind != KIND_DATA:
            return CHAIN_COLUMN_MISMATCH
        key = keys.get(b.node_id)
        if key is None or not crypto.verify(key, b.payload, b.sig):
            return CHAIN_BAD_SIGNATURE
        try:
            r = Reading.from_payload(b.payload)
        except ValueError:
            return CHAIN_COLUMN_MISMATCH
        if (
            r.node_id != b.node_id
            or r.seq != b.seq
            or b.status != r.status
            or b.temp_c is None
            or abs(b.temp_c - r.temp_c) > 1e-9
        ):
            return CHAIN_COLUMN_MISMATCH
        return None

    # ---- eventos (fora da corrente) ---------------------------------------------------

    def add_event(
        self, kind: str, detail: str = "", node_id: int | None = None, rx_ts: int | None = None
    ) -> Event:
        rx_ts = int(time.time()) if rx_ts is None else rx_ts
        with self.lock:
            cur = self.db.execute(
                "INSERT INTO events (rx_ts, kind, node_id, detail) VALUES (?,?,?,?)",
                (rx_ts, kind, node_id, detail),
            )
            self.db.commit()
        return Event(cur.lastrowid, rx_ts, kind, node_id, detail)

    def events(self, limit: int = 100) -> list[Event]:
        """Ultimos eventos, do mais recente para o mais antigo."""
        with self.lock:
            rows = self.db.execute(
                "SELECT id, rx_ts, kind, node_id, detail FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [Event(*r) for r in rows]

    def reset(self) -> None:
        """Apaga tudo (botao "Restaurar demo")."""
        with self.lock:
            self.db.execute("DELETE FROM blocks")
            self.db.execute("DELETE FROM events")
            self.db.execute("DELETE FROM sqlite_sequence WHERE name IN ('blocks','events')")
            self.db.commit()

    def close(self) -> None:
        with self.lock:
            self.db.close()
