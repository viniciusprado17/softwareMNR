import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import make_setup  # noqa: E402

from coldchain.gateway import Result  # noqa: E402
from coldchain.serial_bridge import (  # noqa: E402
    SerialBridge,
    SimulatedReceiver,
    format_rx_line,
    parse_line,
)

MALFORMED = [
    "", "lixo", "RX", "RX,", "RX,-60,9.5", "RX,abc,9.5,00", "RX,-60,x,00", "RX,-60,9.5,0g",
    "RX,-60,9.5,abc", "RX,-60,9.5,00,extra", "ERR", "\x00\xff", b"\xff\xfe\x00RX,1,2,zz",
    "RX,-60,9.5," + "00" * 300, "TX,1,abcd", "   ",
]


class ParseTests(unittest.TestCase):
    def test_rx_line(self):
        p = parse_line("RX,-63,9.5,0102ff\r\n")
        self.assertEqual((p.kind, p.rssi, p.snr, p.data), ("RX", -63, 9.5, b"\x01\x02\xff"))

    def test_bytes_input(self):
        self.assertEqual(parse_line(b"RX,-1,0.0,00\n").data, b"\x00")

    def test_info_and_err(self):
        self.assertEqual(parse_line("INFO,boot ok").text, "boot ok")
        e = parse_line("ERR,-707,crc invalido")
        self.assertEqual((e.kind, e.code, e.text), ("ERR", "-707", "crc invalido"))

    def test_malformed_never_raises(self):
        for line in MALFORMED:
            self.assertIsNone(parse_line(line), repr(line))

    def test_format_roundtrip(self):
        line = format_rx_line(b"\xab" * 88, -63, 9.5)
        self.assertEqual(len(line.split(",")[3]), 176)
        self.assertEqual(parse_line(line).data, b"\xab" * 88)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.key, self.node, self.ledger, self.gw = make_setup()
        self.outcomes = []
        self.bridge = SerialBridge(self.gw, self.outcomes.append)

    def test_malformed_lines_do_not_break_the_bridge(self):
        good = format_rx_line(self.node.make_packet(5.0), -60, 9.0)
        self.bridge.run(MALFORMED + ["INFO,ola", "ERR,1,x", good])
        self.assertEqual([o.result for o in self.outcomes], [Result.ACCEPTED])
        self.assertEqual(self.ledger.blocks()[0].rssi, -60)
        self.assertEqual(self.bridge.stats.errors, 1)
        self.assertEqual(self.bridge.stats.info, 1)

    def test_wrong_length_reaches_gateway(self):
        self.bridge.handle_line("RX,-60,9.0,0102")
        self.assertEqual(self.outcomes[0].result, Result.BAD_LENGTH)

    def test_simulated_mode_feeds_gateway(self):
        sim = SimulatedReceiver(self.node, interval_s=0, seed=1)
        stop = threading.Event()
        lines = sim.lines(self.bridge.stats, stop)
        first = [next(lines) for _ in range(6)]
        self.bridge.run(first)
        self.assertEqual(self.ledger.count(), 5)
        self.assertTrue(all(o.result == Result.ACCEPTED for o in self.outcomes))
        self.assertTrue(self.ledger.verify_chain(self.gw.keys).ok)

    def test_simulated_heat_raises_temperature(self):
        sim = SimulatedReceiver(self.node, interval_s=0, seed=1)
        sim.heat(True)
        self.bridge.run([sim.next_line() for _ in range(20)])
        self.assertGreater(self.ledger.blocks()[-1].temp_c, 8.0)
        self.assertEqual(self.ledger.blocks()[-1].status, 2)


if __name__ == "__main__":
    unittest.main()
