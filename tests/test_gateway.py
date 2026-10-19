import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import make_setup  # noqa: E402

from coldchain import crypto  # noqa: E402
from coldchain.gateway import ANOMALY_STATUS, EVENT_SILENCE, Result  # noqa: E402
from coldchain.node_sim import SimNode  # noqa: E402
from coldchain.packet import Reading  # noqa: E402


class GatewayExtendedTests(unittest.TestCase):
    def setUp(self):
        self.key, self.node, self.ledger, self.gw = make_setup(
            expected_interval_s=10, silence_factor=3)

    def kinds(self):
        return [e.kind for e in reversed(self.ledger.events())]

    def test_rejections_become_events_not_blocks(self):
        pkt = self.node.make_packet(5.0)
        self.gw.receive(pkt)
        self.gw.receive(pkt)  # replay
        bad = bytearray(self.node.make_packet(8.6))
        bad[12] ^= 1
        self.gw.receive(bytes(bad))
        self.gw.receive(b"\x00" * 5)
        self.gw.receive(SimNode(9, crypto.generate_keypair()).make_packet(5.0))
        self.assertEqual(self.ledger.count(), 1)
        self.assertEqual(self.kinds(), ["aceito", "replay", "assinatura_invalida",
                                        "tamanho_invalido", "no_desconhecido"])

    def test_bad_payload(self):
        pkt = bytearray(self.node.make_packet(5.0))
        pkt[0] = 9  # versao desconhecida
        self.assertEqual(self.gw.receive(bytes(pkt)).result, Result.BAD_PAYLOAD)

    def test_status_divergence_is_annotated(self):
        # No mente o status (diz OK a 9 C) mas assina corretamente: aceito com anomalia.
        payload = Reading(1, 1, 0, 9.0, 40.0, 0).to_payload()
        out = self.gw.receive(payload + crypto.sign(self.key, payload))
        self.assertEqual(out.result, Result.ACCEPTED)
        self.assertEqual(out.anomaly, ANOMALY_STATUS)
        self.assertEqual(self.ledger.blocks()[0].anomaly, ANOMALY_STATUS)

    def test_no_anomaly_when_status_matches(self):
        self.assertIsNone(self.gw.receive(self.node.make_packet(8.6)).anomaly)

    def test_rssi_snr_stored(self):
        out = self.gw.receive(self.node.make_packet(5.0), rssi=-71, snr=7.25)
        self.assertEqual((out.block.rssi, out.block.snr), (-71, 7.25))

    def test_silence_event_once_per_period(self):
        t = self.gw.started_at
        self.assertEqual(self.gw.check_silence(t + 20), [])
        self.assertEqual(self.gw.check_silence(t + 31), [1])
        self.assertEqual(self.gw.check_silence(t + 60), [])  # mesmo periodo: nao repete
        self.gw.receive(self.node.make_packet(5.0))
        now = self.gw.last_rx[1]
        self.assertEqual(self.gw.check_silence(now + 5), [])
        self.assertEqual(self.gw.check_silence(now + 31), [1])
        self.assertEqual(self.kinds().count(EVENT_SILENCE), 2)

    def test_reset_node_disabled_by_default(self):
        with self.assertRaises(PermissionError):
            self.gw.reset_node(1)

    def test_reset_node_allows_new_seq_start(self):
        _, node, ledger, gw = make_setup(allow_resync=True)
        for t in (5.0, 5.1, 5.2):
            gw.receive(node.make_packet(t))
        node.seq = 0  # no reiniciou sem NVS
        self.assertEqual(gw.receive(node.make_packet(5.0)).result, Result.REPLAY)
        gw.reset_node(1)
        node.seq = 0
        self.assertEqual(gw.receive(node.make_packet(5.0)).result, Result.ACCEPTED)
        self.assertTrue(ledger.verify_chain(gw.keys).ok)

    def test_last_accepted_packet_tracked(self):
        pkt = self.node.make_packet(5.0)
        self.gw.receive(pkt)
        self.gw.receive(b"x")
        self.assertEqual(self.gw.last_accepted_packet, pkt)


if __name__ == "__main__":
    unittest.main()
