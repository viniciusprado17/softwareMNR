"""Reabrir o gateway simulado com o mesmo banco nao gera replay."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from coldchain.config import load_config  # noqa: E402
from coldchain.gateway import Result  # noqa: E402
from coldchain.serial_bridge import build_gateway, make_sim_node  # noqa: E402


class SimResumeTest(unittest.TestCase):
    def test_sim_node_continues_seq_after_restart(self):
        cfg = load_config()
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "ledger.db")
            gw = build_gateway(cfg, db)
            node = make_sim_node(cfg, gw)
            for _ in range(3):
                out = gw.receive(node.make_packet(5.0))
                self.assertEqual(out.result, Result.ACCEPTED)
            gw.ledger.db.close()

            gw2 = build_gateway(cfg, db)
            node2 = make_sim_node(cfg, gw2)
            self.assertEqual(node2.seq, 3)
            self.assertEqual(gw2.receive(node2.make_packet(5.0)).result, Result.ACCEPTED)
            gw2.ledger.db.close()


if __name__ == "__main__":
    unittest.main()
