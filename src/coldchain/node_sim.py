"""Simulador de no sensor: gera leituras, classifica, assina e monta o pacote de 88 bytes."""
from __future__ import annotations

import random
import time

from cryptography.hazmat.primitives.asymmetric import ec

from . import crypto
from .decision import DEFAULT, Thresholds, classify
from .packet import Reading


class SimNode:
    def __init__(
        self,
        node_id: int,
        private_key: ec.EllipticCurvePrivateKey,
        thresholds: Thresholds = DEFAULT,
        seed: int | None = None,
    ):
        self.node_id = node_id
        self.key = private_key
        self.th = thresholds
        self.seq = 0
        self.rng = random.Random(seed)

    def make_packet(
        self,
        temp_c: float,
        hum_pct: float = 45.0,
        ts: int | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> bytes:
        self.seq += 1
        r = Reading(
            node_id=self.node_id,
            seq=self.seq,
            ts=int(time.time()) if ts is None else ts,
            temp_c=temp_c,
            hum_pct=hum_pct,
            status=classify(temp_c, self.th),
            lat=lat,
            lon=lon,
        )
        payload = r.to_payload()
        return payload + crypto.sign(self.key, payload)

    def random_temp(self, mean: float = 5.0, sd: float = 0.8) -> float:
        return round(self.rng.gauss(mean, sd), 2)
