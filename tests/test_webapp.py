import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import helpers  # noqa: E402,F401

try:
    from fastapi.testclient import TestClient
except (ImportError, RuntimeError):  # fastapi/httpx ausentes: pula
    TestClient = None

from coldchain.config import Config  # noqa: E402
from coldchain.serial_bridge import build_gateway  # noqa: E402


@unittest.skipIf(TestClient is None, "fastapi/httpx nao instalados")
class WebAppTests(unittest.TestCase):
    """Roteiro A a E da Secao 0.3 no modo simulado, pela API."""

    def setUp(self):
        from coldchain.webapp import create_app

        cfg = Config(keys_file="/nao/existe.json")
        self.gw = build_gateway(cfg, ":memory:")
        app = create_app(cfg, self.gw, simulate=True, demo_controls=True, start_bridge=False)
        self.sim = app.state.sim
        self.bridge = app.state.bridge
        self.client = TestClient(app)

    def feed(self, n):
        for _ in range(n):
            self.bridge.handle_line(self.sim.next_line())

    def test_index_and_static(self):
        self.assertIn("Cadeia de Frio", self.client.get("/").text)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)

    def test_access_for_qr_code(self):
        # padrao do teste: escuta so em 127.0.0.1, entao nao ha endereco de rede para o QR
        a = self.client.get("/api/access").json()
        self.assertEqual(set(a), {"host", "port", "lan_open", "urls", "password_required"})
        self.assertFalse(a["lan_open"])
        self.assertEqual(a["urls"], [])
        self.assertFalse(a["password_required"])

    def test_access_lists_lan_urls_when_open_to_network(self):
        from unittest import mock

        from coldchain import webapp

        cfg = Config(keys_file="/nao/existe.json")
        cfg.web.host = "0.0.0.0"
        cfg.web.port = 8123
        gw = build_gateway(cfg, ":memory:")
        with mock.patch.object(webapp, "lan_addresses", return_value=["192.168.0.20"]):
            client = TestClient(webapp.create_app(cfg, gw, simulate=True, start_bridge=False))
            a = client.get("/api/access").json()
        self.assertTrue(a["lan_open"])
        self.assertEqual(a["urls"], ["http://192.168.0.20:8123"])

    def test_installable_app_files(self):
        m = self.client.get("/manifest.webmanifest")
        self.assertEqual(m.status_code, 200)
        self.assertEqual(m.json()["start_url"], "/")
        sw = self.client.get("/sw.js")
        self.assertEqual(sw.status_code, 200)
        self.assertIn("/api/", sw.text)  # o service worker ignora a API
        self.assertEqual(self.client.get("/static/icons/icon-192.png").status_code, 200)

    def test_export_chain_for_independent_verifier(self):
        from coldchain.ledger import GENESIS, _hash

        self.feed(4)
        doc = self.client.get("/api/export/chain").json()
        self.assertEqual(doc["format"], "coldchain-export/1")
        self.assertEqual(doc["curve"], "P-256")
        self.assertEqual(doc["genesis"], GENESIS.hex())
        self.assertEqual(doc["head"], self.client.get("/api/status").json()["chain"]["head"])
        self.assertEqual([len(k) for k in doc["nodes"].values()], [130])
        self.assertEqual(len(doc["blocks"]), 4)
        # round-trip: o documento sozinho basta para refazer a corrente
        prev = bytes.fromhex(doc["genesis"])
        for b in doc["blocks"]:
            self.assertEqual(b["prev_hash"], prev.hex())
            h = _hash(prev, bytes.fromhex(b["payload"]), bytes.fromhex(b["sig"]))
            self.assertEqual(b["hash"], h.hex())
            prev = h
        r = self.client.get("/api/export/chain?download=1")
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertIn("corrente_", r.headers["content-disposition"])

    def test_verifier_page(self):
        r = self.client.get("/verificador")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Verificador independente", r.text)
        self.assertEqual(self.client.get("/static/verifier-core.js").status_code, 200)

    def test_full_demo_flow(self):
        c = self.client
        self.feed(5)
        s = c.get("/api/status").json()
        self.assertEqual(s["chain"]["blocks"], 5)
        self.assertTrue(s["demo_controls"])
        self.assertEqual(s["event_counts"], {"aceito": 5})
        self.assertEqual(len(c.get("/api/readings?limit=3").json()), 3)
        # B: aceito
        self.assertEqual(c.get("/api/events").json()[0]["kind"], "aceito")
        # C: adulteracao
        r = c.post("/api/demo/tamper").json()
        self.assertEqual(r["result"], "assinatura_invalida")
        self.assertEqual(r["forged_temp"], 5.0)
        # D: replay
        self.assertEqual(c.post("/api/demo/replay").json()["result"], "replay")
        # E: corrente integra, depois edicao no banco detectada
        self.assertEqual(c.get("/api/chain/verify").json(),
                         {"ok": True, "bloco_invalido": None, "motivo": None})
        bad = c.post("/api/demo/corrupt-db").json()
        v = c.get("/api/chain/verify").json()
        self.assertFalse(v["ok"])
        self.assertEqual(v["bloco_invalido"], bad["idx"])
        self.assertEqual(v["motivo"], "hash_quebrado")
        # Restaurar
        self.assertTrue(c.post("/api/demo/reset").json()["ok"])
        self.assertEqual(c.get("/api/status").json()["chain"]["blocks"], 0)
        self.assertEqual(c.post("/api/demo/replay").status_code, 409)

    def test_corrupt_targets_alarm_block(self):
        self.client.post("/api/sim/heat", json={"on": True})
        self.feed(15)
        self.client.post("/api/sim/heat", json={"on": False})
        self.feed(15)
        bad = self.client.post("/api/demo/corrupt-db").json()
        self.assertGreater(bad["from_temp"], 7.5)

    def test_password_protects_everything_but_healthz(self):
        from coldchain.webapp import create_app

        cfg = Config(keys_file="/nao/existe.json")
        app = create_app(cfg, build_gateway(cfg, ":memory:"), start_bridge=False, password="lacor")
        c = TestClient(app)
        self.assertEqual(c.get("/").status_code, 401)
        self.assertEqual(c.get("/api/status", auth=("x", "errada")).status_code, 401)
        self.assertEqual(c.get("/api/status", auth=("equipe", "lacor")).status_code, 200)
        self.assertEqual(c.get("/healthz").status_code, 200)

    def test_demo_routes_absent_without_flag(self):
        from coldchain.webapp import create_app

        cfg = Config(keys_file="/nao/existe.json")
        app = create_app(cfg, build_gateway(cfg, ":memory:"), start_bridge=False)
        c = TestClient(app)
        self.assertEqual(c.post("/api/demo/tamper").status_code, 404)
        self.assertEqual(c.post("/api/sim/heat", json={"on": True}).status_code, 404)
        self.assertFalse(c.get("/api/status").json()["demo_controls"])


if __name__ == "__main__":
    unittest.main()
