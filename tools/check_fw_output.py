"""Confere no Python as assinaturas geradas pelo firmware (testes T4/T5, Secao 12.2).

Le linhas de um arquivo, da entrada padrao ou direto da porta serial e verifica:
  SIGNED,<hex 88 bytes>   (firmware/vectest ou teste no PC) com a chave dos vetores
  TX,<seq>,<hex 88 bytes> (firmware do no) com keys/nodes.json
  RX,<rssi>,<snr>,<hex>   (firmware do receptor) com keys/nodes.json

Exemplos:
  python tools/check_fw_output.py --vectors saida.txt
  python tools/check_fw_output.py --vectors --port /dev/ttyUSB0 --seconds 20
  python tools/check_fw_output.py --port /dev/ttyUSB0 --seconds 30   # no real
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from coldchain import crypto
from coldchain.config import load_trusted_keys
from coldchain.packet import PACKET_LEN, Reading, split_packet


def read_lines(args):
    if args.port:
        import serial

        end = time.time() + args.seconds
        with serial.Serial(args.port, args.baud, timeout=1) as ser:
            while time.time() < end:
                line = ser.readline().decode("ascii", errors="replace").strip()
                if line:
                    print(line)
                    yield line
    else:
        f = open(args.file) if args.file and args.file != "-" else sys.stdin
        with f:
            for line in f:
                yield line.strip()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("file", nargs="?", help="arquivo com a saida (padrao: entrada padrao)")
    p.add_argument("--vectors", action="store_true",
                   help="usar a chave de teste de tests/vectors.json e exigir SELFTEST,OK")
    p.add_argument("--keys", default=os.path.join(ROOT, "keys", "nodes.json"))
    p.add_argument("--port")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--seconds", type=float, default=20)
    args = p.parse_args()

    if args.vectors:
        with open(os.path.join(ROOT, "tests", "vectors.json")) as f:
            pub = crypto.public_from_raw(bytes.fromhex(json.load(f)["public_key_hex"]))
        keys = None
    else:
        keys = load_trusted_keys(args.keys)
        if not keys:
            print(f"nenhuma chave em {args.keys}; rode tools/provision_node.py", file=sys.stderr)
            return 2

    checked = bad = 0
    selftest_ok = False
    for line in read_lines(args):
        parts = line.split(",")
        if line == "SELFTEST,OK":
            selftest_ok = True
        if parts[0] == "SIGNED" and len(parts) == 2:
            hexdata = parts[1]
        elif parts[0] == "TX" and len(parts) == 3:
            hexdata = parts[2]
        elif parts[0] == "RX" and len(parts) == 4:
            hexdata = parts[3]
        else:
            continue
        try:
            pkt = bytes.fromhex(hexdata)
            payload, sig = split_packet(pkt)
            reading = Reading.from_payload(payload)
        except ValueError as e:
            print(f"  FALHA: pacote invalido ({e})")
            bad += 1
            continue
        key = pub if args.vectors else keys.get(reading.node_id)
        ok = key is not None and crypto.verify(key, payload, sig)
        checked += 1
        bad += not ok
        print(f"  {'ACEITO' if ok else 'FALHA '} no={reading.node_id} seq={reading.seq} "
              f"T={reading.temp_c:.2f}C ({len(pkt)} bytes de {PACKET_LEN})")

    print(f"verificados={checked} falhas={bad}" + (f" selftest_ok={selftest_ok}" if args.vectors else ""))
    if checked == 0 or bad or (args.vectors and not selftest_ok):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
