"""Gateway: valida pacote recebido (tamanho, assinatura, replay) e grava no ledger."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cryptography.hazmat.primitives.asymmetric import ec

from . import crypto
from .ledger import Ledger
from .packet import Reading, split_packet


class Result(str, Enum):
    ACCEPTED = "aceito"
    BAD_LENGTH = "tamanho_invalido"
    BAD_SIGNATURE = "assinatura_invalida"
    UNKNOWN_NODE = "no_desconhecido"
    REPLAY = "replay"
    BAD_PAYLOAD = "payload_invalido"


@dataclass
class Outcome:
    result: Result
    reading: Reading | None = None


class Gateway:
    def __init__(self, ledger: Ledger, trusted_keys: dict[int, ec.EllipticCurvePublicKey]):
        self.ledger = ledger
        self.keys = trusted_keys

    def receive(self, packet: bytes) -> Outcome:
        try:
            payload, sig = split_packet(packet)
        except ValueError:
            return Outcome(Result.BAD_LENGTH)
        try:
            reading = Reading.from_payload(payload)
        except ValueError:
            return Outcome(Result.BAD_PAYLOAD)
        key = self.keys.get(reading.node_id)
        if key is None:
            return Outcome(Result.UNKNOWN_NODE, reading)
        if not crypto.verify(key, payload, sig):
            return Outcome(Result.BAD_SIGNATURE, reading)
        last = self.ledger.last_seq(reading.node_id)
        if last is not None and reading.seq <= last:
            return Outcome(Result.REPLAY, reading)
        self.ledger.append(reading.node_id, reading.seq, payload, sig)
        return Outcome(Result.ACCEPTED, reading)
