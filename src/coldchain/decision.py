"""Classificacao termica. Faixa padrao 2-8 C (vacinas/orgaos em transporte refrigerado)."""
from __future__ import annotations

from dataclasses import dataclass

from .packet import STATUS_ALARM, STATUS_OK, STATUS_WARN


@dataclass(frozen=True)
class Thresholds:
    low: float = 2.0
    high: float = 8.0
    margin: float = 0.5  # faixa de ALERTA antes de cruzar o limite


DEFAULT = Thresholds()


def classify(temp_c: float, th: Thresholds = DEFAULT) -> int:
    if temp_c < th.low or temp_c > th.high:
        return STATUS_ALARM
    if temp_c < th.low + th.margin or temp_c > th.high - th.margin:
        return STATUS_WARN
    return STATUS_OK
