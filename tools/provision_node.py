"""Gera o par de chaves de um no e distribui as partes (Secao 7.2).

  - chave privada  -> firmware/include/keys.h  (fora do git) e keys/private/node_<id>.pem (fora do git)
  - chave publica  -> keys/nodes.json (cadastro de chaves confiaveis do gateway)

Rodar: python tools/provision_node.py --node-id 1
Se a chave vazar (foto, video, banner, commit), gere outra com --force.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from coldchain import crypto
from coldchain.config import save_trusted_key


def c_array(data: bytes) -> str:
    rows = [", ".join(f"0x{b:02x}" for b in data[i : i + 12]) for i in range(0, len(data), 12)]
    return "\n".join(f"    {r}," for r in rows)


def keys_h(node_id: int, priv: bytes, pub_xy: bytes) -> str:
    return f"""// GERADO por tools/provision_node.py. NAO COMMITAR (esta no .gitignore).
// Chave embutida no firmware so no prototipo; em producao, elemento seguro.
#pragma once

#include <stdint.h>

#define KEYS_NODE_ID {node_id}

// Escalar privado P-256, 32 bytes big-endian.
static const uint8_t NODE_PRIVATE_KEY[32] = {{
{c_array(priv)}
}};
// Chave publica X||Y (64 bytes), conferida no boot.
static const uint8_t NODE_PUBLIC_KEY[64] = {{
{c_array(pub_xy)}
}};
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--node-id", type=int, required=True)
    p.add_argument("--force", action="store_true", help="substitui a chave existente do no")
    p.add_argument("--keys-file", default=os.path.join(ROOT, "keys", "nodes.json"))
    p.add_argument("--header", default=os.path.join(ROOT, "firmware", "include", "keys.h"))
    args = p.parse_args()

    pem_path = os.path.join(ROOT, "keys", "private", f"node_{args.node_id}.pem")
    if os.path.exists(pem_path) and not args.force:
        print(f"ja existe {pem_path}; use --force para gerar outra", file=sys.stderr)
        return 1

    key = crypto.generate_keypair()
    priv = key.private_numbers().private_value.to_bytes(32, "big")
    pub = crypto.public_bytes_raw(key.public_key())

    os.makedirs(os.path.dirname(pem_path), exist_ok=True)
    with open(os.open(pem_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
        f.write(crypto.private_to_pem(key))
    with open(args.header, "w") as f:
        f.write(keys_h(args.node_id, priv, pub[1:]))
    save_trusted_key(args.keys_file, args.node_id, pub)

    print(f"no {args.node_id} provisionado")
    print(f"  firmware : {args.header}  (NAO commitar)")
    print(f"  privada  : {pem_path}  (NAO commitar; usada pelo modo --simulate)")
    print(f"  publica  : {args.keys_file}  -> {pub.hex()[:18]}...")
    print("Proximo passo: gravar o firmware do no (firmware/node) com este keys.h.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
