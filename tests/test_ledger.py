import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import make_setup  # noqa: E402

from coldchain import crypto  # noqa: E402
from coldchain.ledger import (  # noqa: E402
    CHAIN_BAD_SIGNATURE,
    CHAIN_BROKEN_HASH,
    CHAIN_COLUMN_MISMATCH,
    CHAIN_PREV_MISMATCH,
    KIND_DATA,
    Ledger,
)
from coldchain.packet import Reading  # noqa: E402


class LedgerExtendedTests(unittest.TestCase):
    def setUp(self):
        self.key, self.node, self.ledger, self.gw = make_setup()
        for t in (5.0, 5.2, 8.6, 5.1):
            self.gw.receive(self.node.make_packet(t), rssi=-60, snr=9.5, rx_ts=1_800_000_000)

    def test_columns_filled(self):
        b = self.ledger.blocks()[2]
        self.assertEqual(b.rssi, -60)
        self.assertAlmostEqual(b.snr, 9.5)
        self.assertEqual(b.rx_ts, 1_800_000_000)
        self.assertAlmostEqual(b.temp_c, 8.6)
        self.assertEqual(b.status, 2)
        self.assertEqual(b.kind, KIND_DATA)

    def test_chain_ok_with_signatures(self):
        self.assertTrue(self.ledger.verify_chain(self.gw.keys).ok)

    def test_broken_hash(self):
        self.ledger.db.execute("UPDATE blocks SET payload=? WHERE idx=3",
                               (Reading.from_payload(self.ledger.blocks()[0].payload).to_payload(),))
        self.assertEqual(self.ledger.verify_chain(self.gw.keys), (False, 3, CHAIN_BROKEN_HASH))

    def test_prev_hash_mismatch(self):
        self.ledger.db.execute("UPDATE blocks SET prev_hash=? WHERE idx=2", (b"\x11" * 32,))
        self.assertEqual(self.ledger.verify_chain(), (False, 2, CHAIN_PREV_MISMATCH))

    def test_column_mismatch_detected(self):
        # Editar so a copia decodificada nao quebra o hash, mas a verificacao completa acusa.
        self.ledger.db.execute("UPDATE blocks SET temp_c=5.0, status=0 WHERE idx=3")
        self.assertTrue(self.ledger.verify_chain().ok)
        self.assertEqual(self.ledger.verify_chain(self.gw.keys), (False, 3, CHAIN_COLUMN_MISMATCH))

    def test_bad_signature_detected(self):
        # Atacante reescreve payload, sig e recalcula toda a corrente: so a assinatura acusa.
        blocks = self.ledger.blocks()
        forged = bytearray(blocks[1].payload)
        forged[12] ^= 1
        self.ledger.db.execute("DELETE FROM blocks")
        other = Ledger()
        for i, b in enumerate(blocks):
            payload = bytes(forged) if i == 1 else b.payload
            other.append(b.node_id, b.seq, payload, b.sig)
        for b in other.blocks():
            self.ledger.db.execute(
                "INSERT INTO blocks (idx,node_id,seq,payload,sig,prev_hash,hash,temp_c,status,kind)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (b.idx, b.node_id, b.seq, b.payload, b.sig, b.prev_hash, b.hash, b.temp_c,
                 b.status, b.kind))
        self.assertTrue(self.ledger.verify_chain().ok)
        self.assertEqual(self.ledger.verify_chain(self.gw.keys), (False, 2, CHAIN_BAD_SIGNATURE))

    def test_blocks_limit_returns_latest(self):
        self.assertEqual([b.seq for b in self.ledger.blocks(limit=2)], [3, 4])

    def test_reset(self):
        self.ledger.reset()
        self.assertEqual(self.ledger.count(), 0)
        self.assertEqual(self.ledger.events(), [])
        self.assertIsNone(self.ledger.last_seq(1))

    def test_resync_block(self):
        self.ledger.append_resync(1)
        self.assertIsNone(self.ledger.last_seq(1))
        self.assertTrue(self.ledger.verify_chain(self.gw.keys).ok)
        self.ledger.db.execute("UPDATE blocks SET kind='data' WHERE idx=5")
        self.assertEqual(self.ledger.verify_chain(self.gw.keys).reason, CHAIN_BAD_SIGNATURE)

    def test_kind_flip_to_resync_detected(self):
        # Marcar um bloco de dados como "resync" para pular a assinatura nao funciona.
        self.ledger.db.execute("UPDATE blocks SET kind='resync' WHERE idx=2")
        self.assertEqual(self.ledger.verify_chain(self.gw.keys), (False, 2, CHAIN_COLUMN_MISMATCH))


class LedgerMigrationTests(unittest.TestCase):
    def test_migrates_old_schema(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "old.db")
            db = sqlite3.connect(path)
            db.execute("""CREATE TABLE blocks (idx INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER NOT NULL, seq INTEGER NOT NULL, payload BLOB NOT NULL,
                sig BLOB NOT NULL, prev_hash BLOB NOT NULL, hash BLOB NOT NULL)""")
            db.commit()
            db.close()
            ledger = Ledger(path)
            key = crypto.generate_keypair()
            payload = Reading(1, 1, 0, 5.0, 40.0, 0).to_payload()
            ledger.append(1, 1, payload, crypto.sign(key, payload))
            self.assertTrue(ledger.verify_chain({1: key.public_key()}).ok)
            ledger.close()


if __name__ == "__main__":
    unittest.main()
