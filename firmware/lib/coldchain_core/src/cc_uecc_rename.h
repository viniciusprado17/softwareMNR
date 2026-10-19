// Renomeia os simbolos publicos da micro-ecc para cc_uECC_* (conflito com o tinycrypt
// embutido no libbt do ESP-IDF). Incluir ANTES de uecc/uECC.h. Ver uecc/README.md.
#pragma once

#define uECC_compress cc_uECC_compress
#define uECC_compute_public_key cc_uECC_compute_public_key
#define uECC_curve_private_key_size cc_uECC_curve_private_key_size
#define uECC_curve_public_key_size cc_uECC_curve_public_key_size
#define uECC_decompress cc_uECC_decompress
#define uECC_get_rng cc_uECC_get_rng
#define uECC_make_key cc_uECC_make_key
#define uECC_secp160r1 cc_uECC_secp160r1
#define uECC_secp192r1 cc_uECC_secp192r1
#define uECC_secp224r1 cc_uECC_secp224r1
#define uECC_secp256k1 cc_uECC_secp256k1
#define uECC_secp256r1 cc_uECC_secp256r1
#define uECC_set_rng cc_uECC_set_rng
#define uECC_shared_secret cc_uECC_shared_secret
#define uECC_sign cc_uECC_sign
#define uECC_sign_deterministic cc_uECC_sign_deterministic
#define uECC_sign_with_k cc_uECC_sign_with_k
#define uECC_valid_public_key cc_uECC_valid_public_key
#define uECC_verify cc_uECC_verify

// So a curva usada pelo projeto (economiza flash).
#define uECC_SUPPORTS_secp160r1 0
#define uECC_SUPPORTS_secp192r1 0
#define uECC_SUPPORTS_secp224r1 0
#define uECC_SUPPORTS_secp256k1 0
#define uECC_SUPPORTS_secp256r1 1
