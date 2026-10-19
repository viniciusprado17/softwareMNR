// MODELO. O arquivo real firmware/include/keys.h e gerado por:
//   python tools/provision_node.py --node-id 1
// e NUNCA vai para o git (.gitignore). Chave embutida no firmware so no prototipo;
// em producao seria um elemento seguro (ex.: ATECC608).
#pragma once

#include <stdint.h>

#define KEYS_NODE_ID 1

// Escalar privado P-256, 32 bytes big-endian.
static const uint8_t NODE_PRIVATE_KEY[32] = {0};
// Chave publica X||Y (64 bytes), conferida no boot.
static const uint8_t NODE_PUBLIC_KEY[64] = {0};
