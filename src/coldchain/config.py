"""Configuracao do gateway (config.toml) e cadastro de chaves publicas (keys/nodes.json).

Nenhum valor magico espalhado pelo codigo: tudo que e ajustavel vem daqui.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.asymmetric import ec

from . import crypto
from .decision import Thresholds

try:  # Python 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # Python 3.10: pip install tomli
    import tomli as _toml  # type: ignore[no-redef]

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CONFIG = os.path.join(ROOT, "config.toml")


@dataclass
class SerialConfig:
    port: str = "/dev/ttyUSB0"
    baud: int = 115200
    reconnect_s: float = 2.0


@dataclass
class NodeConfig:
    expected_interval_s: float = 10.0  # intervalo de envio do no (artigo: 60 s)
    silence_factor: int = 3  # silencio = nenhum pacote por N intervalos


@dataclass
class WebConfig:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class SimConfig:
    node_id: int = 1
    interval_s: float = 2.0
    seed: int = 42


@dataclass
class Config:
    db_path: str = "coldchain.db"
    keys_file: str = "keys/nodes.json"
    log_file: str = "logs/gateway.log"
    allow_resync: bool = False  # --reset-node: desligado por padrao
    thresholds: Thresholds = field(default_factory=Thresholds)
    serial: SerialConfig = field(default_factory=SerialConfig)
    node: NodeConfig = field(default_factory=NodeConfig)
    web: WebConfig = field(default_factory=WebConfig)
    sim: SimConfig = field(default_factory=SimConfig)

    def resolve(self, path: str) -> str:
        """Caminhos relativos sao relativos a raiz do repositorio."""
        if path == ":memory:" or os.path.isabs(path):
            return path
        return os.path.join(ROOT, path)


def load_config(path: str | None = None) -> Config:
    """Le config.toml. Arquivo ausente = valores padrao."""
    path = path or DEFAULT_CONFIG
    cfg = Config()
    if not os.path.exists(path):
        return cfg
    with open(path, "rb") as f:
        data = _toml.load(f)
    gw = data.get("gateway", {})
    cfg.db_path = gw.get("db_path", cfg.db_path)
    cfg.keys_file = gw.get("keys_file", cfg.keys_file)
    cfg.log_file = gw.get("log_file", cfg.log_file)
    cfg.allow_resync = bool(gw.get("allow_resync", cfg.allow_resync))
    th = data.get("thresholds", {})
    cfg.thresholds = Thresholds(
        low=float(th.get("low", cfg.thresholds.low)),
        high=float(th.get("high", cfg.thresholds.high)),
        margin=float(th.get("margin", cfg.thresholds.margin)),
    )
    cfg.serial = SerialConfig(**{**cfg.serial.__dict__, **data.get("serial", {})})
    cfg.node = NodeConfig(**{**cfg.node.__dict__, **data.get("node", {})})
    cfg.web = WebConfig(**{**cfg.web.__dict__, **data.get("web", {})})
    cfg.sim = SimConfig(**{**cfg.sim.__dict__, **data.get("sim", {})})
    return cfg


def load_trusted_keys(path: str) -> dict[int, ec.EllipticCurvePublicKey]:
    """keys/nodes.json: {"<node_id>": "<chave publica 65 bytes em hex>"}. Ausente = vazio."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return {int(k): crypto.public_from_raw(bytes.fromhex(v)) for k, v in data.items()}


def save_trusted_key(path: str, node_id: int, public_raw: bytes) -> None:
    data: dict[str, str] = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    data[str(node_id)] = public_raw.hex()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(dict(sorted(data.items(), key=lambda kv: int(kv[0]))), f, indent=2)
        f.write("\n")
