"""Descobre qual porta COM e a Heltec RECEPTORA e qual e a TRANSMISSORA (e o Uno).

Com duas Heltec no mesmo notebook as portas mudam a cada vez que se tira e poe o cabo.
O gateway precisa da porta da RECEPTORA (linhas RX,...). Se apontar para a transmissora,
a tela fica parada mesmo com tudo funcionando.

Uso (com o gateway FECHADO, porque so um programa pode abrir cada porta):
  python tools/achar_portas.py
"""
from __future__ import annotations

import sys
import time

import serial
from serial.tools import list_ports

ESPERA_S = 12  # o no transmite a cada 10 s; o receptor imprime INFO ao ligar


def identifica(porta: str) -> str:
    try:
        s = serial.Serial(porta, 115200, timeout=0.5)
    except serial.SerialException as e:
        return f"nao abriu ({e}); feche o gateway/monitor que usa esta porta"
    linhas = []
    fim = time.time() + ESPERA_S
    with s:
        while time.time() < fim:
            t = s.readline().decode("ascii", errors="replace").strip()
            if not t:
                continue
            linhas.append(t)
            if t.startswith("INFO,receptor") or t.startswith("RX,"):
                return "RECEPTORA  (use esta no gateway)"
            if t.startswith("TX,") or "fw=node" in t or t.startswith("INFO,uno"):
                return "TRANSMISSORA (no; nao use no gateway)"
            if t.startswith("T:") or "SHT31" in t:
                return "ARDUINO UNO"
    if not linhas:
        return "sem resposta em 12 s (aperte RST na placa e rode de novo)"
    return "desconhecida; primeira linha: " + linhas[0][:60]


def main() -> int:
    quieto = "--so-porta" in sys.argv  # usado pelo iniciar_demo.bat
    portas = list(list_ports.comports())
    if not portas:
        if not quieto:
            print("Nenhuma porta serial. Confira os cabos de dados.")
        return 1
    if not quieto:
        print(f"Lendo cada porta por ate {ESPERA_S} s...\n")
    receptora = None
    for p in portas:
        if quieto and p.vid != 0x10C4:  # so as Heltec (CP210x)
            continue
        papel = identifica(p.device)
        if not quieto:
            print(f"  {p.device:6} {p.description[:40]:40} -> {papel}")
        if papel.startswith("RECEPTORA"):
            receptora = p.device
            if quieto:
                break
    if quieto:
        print(receptora or "")
        return 0 if receptora else 1
    print()
    if receptora:
        print("Abra a tela com:")
        print(f"  .\\run_gateway.bat --port {receptora} --demo-controls")
        return 0
    print("Receptora nao encontrada. Ela precisa estar no cabo de DADOS, com o firmware receiver.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
