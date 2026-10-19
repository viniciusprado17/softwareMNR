"""Formato binario do pacote de leitura. Fonte da verdade para o firmware.

Layout (big-endian, 24 bytes de payload):
  ver      u8   versao do formato (1)
  node_id  u16  identificador do no
  seq      u32  contador monotonico por no (anti-replay)
  ts       u32  unix time (segundos)
  temp     i16  temperatura em centesimos de grau C
  hum      u16  umidade relativa em centesimos de %
  status   u8   0=OK, 1=ALERTA, 2=ALARME
  lat      i32  latitude  em microgramos (graus * 1e6), 0x7FFFFFFF = invalido
  lon      i32  longitude em microgramos (graus * 1e6), 0x7FFFFFFF = invalido

Pacote enviado = payload (24) + assinatura r||s (64) = 88 bytes.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

VERSION = 1
FMT = ">BHIIhHBii"
PAYLOAD_LEN = struct.calcsize(FMT)  # 24
SIG_LEN = 64
PACKET_LEN = PAYLOAD_LEN + SIG_LEN  # 88
GPS_INVALID = 0x7FFFFFFF

STATUS_OK, STATUS_WARN, STATUS_ALARM = 0, 1, 2
STATUS_NAMES = {STATUS_OK: "OK", STATUS_WARN: "ALERTA", STATUS_ALARM: "ALARME"}


@dataclass(frozen=True)
class Reading:
    node_id: int
    seq: int
    ts: int
    temp_c: float
    hum_pct: float
    status: int
    lat: Optional[float] = None
    lon: Optional[float] = None
    ver: int = VERSION

    def to_payload(self) -> bytes:
        lat = GPS_INVALID if self.lat is None else round(self.lat * 1e6)
        lon = GPS_INVALID if self.lon is None else round(self.lon * 1e6)
        return struct.pack(
            FMT,
            self.ver,
            self.node_id,
            self.seq,
            self.ts,
            round(self.temp_c * 100),
            round(self.hum_pct * 100),
            self.status,
            lat,
            lon,
        )

    @staticmethod
    def from_payload(data: bytes) -> "Reading":
        if len(data) != PAYLOAD_LEN:
            raise ValueError(f"payload deve ter {PAYLOAD_LEN} bytes, veio {len(data)}")
        ver, node_id, seq, ts, t, h, status, lat, lon = struct.unpack(FMT, data)
        if ver != VERSION:
            raise ValueError(f"versao de pacote desconhecida: {ver}")
        if status not in STATUS_NAMES:
            raise ValueError(f"status invalido: {status}")
        return Reading(
            node_id=node_id,
            seq=seq,
            ts=ts,
            temp_c=t / 100,
            hum_pct=h / 100,
            status=status,
            lat=None if lat == GPS_INVALID else lat / 1e6,
            lon=None if lon == GPS_INVALID else lon / 1e6,
            ver=ver,
        )


def split_packet(packet: bytes) -> tuple[bytes, bytes]:
    """Separa payload e assinatura de um pacote recebido."""
    if len(packet) != PACKET_LEN:
        raise ValueError(f"pacote deve ter {PACKET_LEN} bytes, veio {len(packet)}")
    return packet[:PAYLOAD_LEN], packet[PAYLOAD_LEN:]
