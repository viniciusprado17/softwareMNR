// ECDSA P-256 (secp256r1) sobre SHA-256 do payload, assinatura bruta r||s (64 bytes).
// Biblioteca: micro-ecc. Assinatura deterministica (uECC_sign_deterministic: nonce derivado
// por HMAC-SHA-256 da chave e do hash, no estilo da RFC 6979): nao depende do gerador de
// numeros aleatorios do ESP32, cuja falha revelaria a chave privada (Secao 7.4).
// Obs.: os bytes nao coincidem com o RFC 6979 do OpenSSL; compare a VALIDADE, nao a igualdade.
#pragma once

#include <stddef.h>
#include <stdint.h>

#define CC_PRIV_LEN 32
#define CC_PUB_LEN 64  // X||Y, sem o prefixo 0x04 (formato da micro-ecc)

// Assina `len` bytes. Retorna false em caso de erro.
bool cc_sign(const uint8_t priv[CC_PRIV_LEN], const uint8_t* msg, size_t len, uint8_t sig[64]);

// Verifica a assinatura de `len` bytes com a chave publica X||Y.
bool cc_verify(const uint8_t pub[CC_PUB_LEN], const uint8_t* msg, size_t len,
               const uint8_t sig[64]);

// Deriva a chave publica X||Y a partir da privada.
bool cc_public_from_private(const uint8_t priv[CC_PRIV_LEN], uint8_t pub[CC_PUB_LEN]);

// Gerador opcional para mascaramento contra canal lateral (ex.: esp_fill_random).
typedef int (*CcRng)(uint8_t* dest, unsigned size);
void cc_set_rng(CcRng rng);
