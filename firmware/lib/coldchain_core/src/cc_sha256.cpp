#include "cc_sha256.h"

#include <string.h>

static const uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
    0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
    0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
    0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
    0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
    0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
    0xc67178f2};

static inline uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }

static void transform(CcSha256* ctx, const uint8_t* block) {
  uint32_t w[64];
  for (int i = 0; i < 16; i++) {
    w[i] = ((uint32_t)block[4 * i] << 24) | ((uint32_t)block[4 * i + 1] << 16) |
           ((uint32_t)block[4 * i + 2] << 8) | block[4 * i + 3];
  }
  for (int i = 16; i < 64; i++) {
    uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
    uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }
  uint32_t a = ctx->state[0], b = ctx->state[1], c = ctx->state[2], d = ctx->state[3];
  uint32_t e = ctx->state[4], f = ctx->state[5], g = ctx->state[6], h = ctx->state[7];
  for (int i = 0; i < 64; i++) {
    uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
    uint32_t ch = (e & f) ^ (~e & g);
    uint32_t t1 = h + S1 + ch + K[i] + w[i];
    uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
    uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
    uint32_t t2 = S0 + maj;
    h = g;
    g = f;
    f = e;
    e = d + t1;
    d = c;
    c = b;
    b = a;
    a = t1 + t2;
  }
  ctx->state[0] += a;
  ctx->state[1] += b;
  ctx->state[2] += c;
  ctx->state[3] += d;
  ctx->state[4] += e;
  ctx->state[5] += f;
  ctx->state[6] += g;
  ctx->state[7] += h;
}

void cc_sha256_init(CcSha256* ctx) {
  static const uint32_t H0[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                                 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  memcpy(ctx->state, H0, sizeof(H0));
  ctx->bitlen = 0;
  ctx->buflen = 0;
}

void cc_sha256_update(CcSha256* ctx, const uint8_t* data, size_t len) {
  for (size_t i = 0; i < len; i++) {
    ctx->buf[ctx->buflen++] = data[i];
    if (ctx->buflen == CC_SHA256_BLOCK) {
      transform(ctx, ctx->buf);
      ctx->bitlen += 512;
      ctx->buflen = 0;
    }
  }
}

void cc_sha256_final(CcSha256* ctx, uint8_t out[CC_SHA256_LEN]) {
  uint64_t bitlen = ctx->bitlen + (uint64_t)ctx->buflen * 8;
  size_t i = ctx->buflen;
  ctx->buf[i++] = 0x80;
  if (i > 56) {
    while (i < CC_SHA256_BLOCK) ctx->buf[i++] = 0;
    transform(ctx, ctx->buf);
    i = 0;
  }
  while (i < 56) ctx->buf[i++] = 0;
  for (int j = 7; j >= 0; j--) ctx->buf[i++] = (uint8_t)(bitlen >> (8 * j));
  transform(ctx, ctx->buf);
  for (int j = 0; j < 8; j++) {
    out[4 * j] = (uint8_t)(ctx->state[j] >> 24);
    out[4 * j + 1] = (uint8_t)(ctx->state[j] >> 16);
    out[4 * j + 2] = (uint8_t)(ctx->state[j] >> 8);
    out[4 * j + 3] = (uint8_t)ctx->state[j];
  }
}

void cc_sha256(const uint8_t* data, size_t len, uint8_t out[CC_SHA256_LEN]) {
  CcSha256 ctx;
  cc_sha256_init(&ctx);
  cc_sha256_update(&ctx, data, len);
  cc_sha256_final(&ctx, out);
}
