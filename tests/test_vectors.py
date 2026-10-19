import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from coldchain import crypto
from coldchain.packet import PACKET_LEN, Reading, split_packet

PATH = os.path.join(os.path.dirname(__file__), "vectors.json")


class VectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PATH) as f:
            cls.data = json.load(f)
        cls.pub = crypto.public_from_raw(bytes.fromhex(cls.data["public_key_hex"]))

    def test_public_key_shape(self):
        raw = bytes.fromhex(self.data["public_key_hex"])
        self.assertEqual(len(raw), 65)
        self.assertEqual(raw[0], 4)

    def test_vectors(self):
        for v in self.data["vectors"]:
            pkt = bytes.fromhex(v["packet_hex"])
            self.assertEqual(len(pkt), PACKET_LEN)
            payload, sig = split_packet(pkt)
            ok = crypto.verify(self.pub, payload, sig)
            self.assertEqual(ok, v["expect"] == "valid", v.get("note", v["payload_hex"]))

    def test_decoded_fields_match(self):
        for v in self.data["vectors"]:
            if "reading" not in v:
                continue
            r = Reading.from_payload(bytes.fromhex(v["payload_hex"]))
            exp = v["reading"]
            self.assertEqual(r.node_id, exp["node_id"])
            self.assertEqual(r.seq, exp["seq"])
            self.assertAlmostEqual(r.temp_c, exp["temp_c"], places=2)
            self.assertEqual(r.status, exp["status"])


if __name__ == "__main__":
    unittest.main()
