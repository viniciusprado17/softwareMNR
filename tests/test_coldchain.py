import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from coldchain import crypto
from coldchain.decision import classify
from coldchain.gateway import Gateway, Result
from coldchain.ledger import Ledger
from coldchain.node_sim import SimNode
from coldchain.packet import (
    PACKET_LEN,
    PAYLOAD_LEN,
    STATUS_ALARM,
    STATUS_OK,
    STATUS_WARN,
    Reading,
)


class PacketTests(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(PAYLOAD_LEN, 24)
        self.assertEqual(PACKET_LEN, 88)

    def test_roundtrip(self):
        r = Reading(7, 123, 1_800_000_000, 5.25, 43.5, STATUS_OK, -10.9472, -37.0731)
        r2 = Reading.from_payload(r.to_payload())
        self.assertEqual(r2.node_id, 7)
        self.assertEqual(r2.seq, 123)
        self.assertAlmostEqual(r2.temp_c, 5.25)
        self.assertAlmostEqual(r2.lat, -10.9472, places=5)

    def test_gps_invalid(self):
        r = Reading.from_payload(Reading(1, 1, 1, 5.0, 40.0, 0).to_payload())
        self.assertIsNone(r.lat)
        self.assertIsNone(r.lon)

    def test_negative_temp(self):
        r = Reading.from_payload(Reading(1, 1, 1, -3.5, 40.0, STATUS_ALARM).to_payload())
        self.assertAlmostEqual(r.temp_c, -3.5)


class DecisionTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify(5.0), STATUS_OK)
        self.assertEqual(classify(7.8), STATUS_WARN)
        self.assertEqual(classify(2.3), STATUS_WARN)
        self.assertEqual(classify(8.1), STATUS_ALARM)
        self.assertEqual(classify(1.9), STATUS_ALARM)
        self.assertEqual(classify(8.0), STATUS_WARN)


class CryptoTests(unittest.TestCase):
    def test_sign_verify(self):
        k = crypto.generate_keypair()
        sig = crypto.sign(k, b"abc")
        self.assertEqual(len(sig), 64)
        self.assertTrue(crypto.verify(k.public_key(), b"abc", sig))
        self.assertFalse(crypto.verify(k.public_key(), b"abd", sig))

    def test_raw_public_key_roundtrip(self):
        k = crypto.generate_keypair()
        raw = crypto.public_bytes_raw(k.public_key())
        self.assertEqual(len(raw), 65)
        self.assertEqual(raw[0], 4)
        pub = crypto.public_from_raw(raw)
        self.assertTrue(crypto.verify(pub, b"x", crypto.sign(k, b"x")))

    def test_pem_roundtrip(self):
        k = crypto.generate_keypair()
        k2 = crypto.private_from_pem(crypto.private_to_pem(k))
        self.assertTrue(crypto.verify(k.public_key(), b"y", crypto.sign(k2, b"y")))


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.key = crypto.generate_keypair()
        self.node = SimNode(1, self.key, seed=1)
        self.ledger = Ledger()
        self.gw = Gateway(self.ledger, {1: self.key.public_key()})

    def test_accepts_valid(self):
        self.assertEqual(self.gw.receive(self.node.make_packet(5.0)).result, Result.ACCEPTED)
        self.assertEqual(len(self.ledger.blocks()), 1)

    def test_rejects_tampered_payload(self):
        pkt = bytearray(self.node.make_packet(8.6))
        pkt[13] ^= 0x01  # altera um byte da temperatura
        self.assertEqual(self.gw.receive(bytes(pkt)).result, Result.BAD_SIGNATURE)
        self.assertEqual(len(self.ledger.blocks()), 0)

    def test_rejects_tampered_signature(self):
        pkt = bytearray(self.node.make_packet(5.0))
        pkt[-1] ^= 0x01
        self.assertEqual(self.gw.receive(bytes(pkt)).result, Result.BAD_SIGNATURE)

    def test_rejects_replay(self):
        pkt = self.node.make_packet(5.0)
        self.assertEqual(self.gw.receive(pkt).result, Result.ACCEPTED)
        self.assertEqual(self.gw.receive(pkt).result, Result.REPLAY)

    def test_rejects_bad_length(self):
        self.assertEqual(self.gw.receive(b"\x01" * 10).result, Result.BAD_LENGTH)

    def test_rejects_unknown_node(self):
        other = SimNode(5, crypto.generate_keypair())
        self.assertEqual(self.gw.receive(other.make_packet(5.0)).result, Result.UNKNOWN_NODE)

    def test_rejects_wrong_key(self):
        impostor = SimNode(1, crypto.generate_keypair())
        self.assertEqual(self.gw.receive(impostor.make_packet(5.0)).result, Result.BAD_SIGNATURE)


class LedgerTests(unittest.TestCase):
    def test_chain_detects_tamper(self):
        key = crypto.generate_keypair()
        node = SimNode(1, key)
        ledger = Ledger()
        gw = Gateway(ledger, {1: key.public_key()})
        for t in (5.0, 5.2, 4.9, 5.1):
            gw.receive(node.make_packet(t))
        self.assertEqual(ledger.verify_chain(), (True, None))
        ledger.db.execute("UPDATE blocks SET payload=? WHERE idx=2", (b"\x00" * 24,))
        ok, bad = ledger.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(bad, 2)


if __name__ == "__main__":
    unittest.main()
