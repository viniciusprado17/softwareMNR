// SHA-256 portatil (FIPS 180-4), sem dependencia do mbedTLS.
// Motivo: a API do mbedTLS muda entre o core Arduino-ESP32 2.x e 3.x (Secao 7.4 da
// especificacao). Com esta implementacao o mesmo codigo roda no ESP32 e no PC (testes).
#pragma once

#include <stddef.h>
#include <stdint.h>

#define CC_SHA256_LEN 32
#define CC_SHA256_BLOCK 64

struct CcSha256 {
  uint32_t state[8];
  uint64_t bitlen;
  uint8_t buf[CC_SHA256_BLOCK];
  size_t buflen;
};

void cc_sha256_init(CcSha256* ctx);
void cc_sha256_update(CcSha256* ctx, const uint8_t* data, size_t len);
void cc_sha256_final(CcSha256* ctx, uint8_t out[CC_SHA256_LEN]);
void cc_sha256(const uint8_t* data, size_t len, uint8_t out[CC_SHA256_LEN]);
