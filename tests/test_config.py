import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import helpers  # noqa: E402,F401

from coldchain import crypto  # noqa: E402
from coldchain.config import ROOT, load_config, load_trusted_keys, save_trusted_key  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_repo_config_loads(self):
        cfg = load_config(os.path.join(ROOT, "config.toml"))
        self.assertEqual((cfg.thresholds.low, cfg.thresholds.high), (2.0, 8.0))
        self.assertEqual(cfg.serial.baud, 115200)
        self.assertFalse(cfg.allow_resync)

    def test_missing_file_gives_defaults(self):
        cfg = load_config("/nao/existe.toml")
        self.assertEqual(cfg.node.silence_factor, 3)

    def test_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('[thresholds]\nhigh = 7.5\n[web]\nport = 9000\n')
        try:
            cfg = load_config(f.name)
            self.assertEqual(cfg.thresholds.high, 7.5)
            self.assertEqual(cfg.thresholds.low, 2.0)
            self.assertEqual(cfg.web.port, 9000)
        finally:
            os.unlink(f.name)

    def test_keys_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nodes.json")
            self.assertEqual(load_trusted_keys(path), {})
            k = crypto.generate_keypair()
            save_trusted_key(path, 3, crypto.public_bytes_raw(k.public_key()))
            keys = load_trusted_keys(path)
            self.assertTrue(crypto.verify(keys[3], b"m", crypto.sign(k, b"m")))


if __name__ == "__main__":
    unittest.main()
