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
