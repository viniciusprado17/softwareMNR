#include "cc_signer.h"

#include <uECC.h>

#include "cc_sha256.h"

namespace {

struct Sha256HashContext {
  uECC_HashContext uecc;
  CcSha256 ctx;
};

void init_sha256(const uECC_HashContext* base) {
  cc_sha256_init(&((Sha256HashContext*)base)->ctx);
}

void update_sha256(const uECC_HashContext* base, const uint8_t* msg, unsigned size) {
  cc_sha256_update(&((Sha256HashContext*)base)->ctx, msg, size);
}

void finish_sha256(const uECC_HashContext* base, uint8_t* out) {
  cc_sha256_final(&((Sha256HashContext*)base)->ctx, out);
}

}  // namespace

bool cc_sign(const uint8_t priv[CC_PRIV_LEN], const uint8_t* msg, size_t len, uint8_t sig[64]) {
  uint8_t hash[CC_SHA256_LEN];
  cc_sha256(msg, len, hash);
  uint8_t tmp[2 * CC_SHA256_LEN + CC_SHA256_BLOCK];
  Sha256HashContext hctx = {
      {&init_sha256, &update_sha256, &finish_sha256, CC_SHA256_BLOCK, CC_SHA256_LEN, tmp}, {}};
  return uECC_sign_deterministic(priv, hash, sizeof(hash), &hctx.uecc, sig, uECC_secp256r1()) ==
         1;
}

bool cc_verify(const uint8_t pub[CC_PUB_LEN], const uint8_t* msg, size_t len,
               const uint8_t sig[64]) {
  uint8_t hash[CC_SHA256_LEN];
  cc_sha256(msg, len, hash);
  return uECC_verify(pub, hash, sizeof(hash), sig, uECC_secp256r1()) == 1;
}

bool cc_public_from_private(const uint8_t priv[CC_PRIV_LEN], uint8_t pub[CC_PUB_LEN]) {
  return uECC_compute_public_key(priv, pub, uECC_secp256r1()) == 1;
}

void cc_set_rng(CcRng rng) { uECC_set_rng(rng); }
