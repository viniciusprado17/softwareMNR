# Formato do pacote (v1)

Big-endian. Payload de 24 bytes + assinatura bruta r||s de 64 bytes = **88 bytes**.

| Offset | Tam | Campo | Tipo | Notas |
|---|---|---|---|---|
| 0 | 1 | ver | u8 | 1 |
| 1 | 2 | node_id | u16 | |
| 3 | 4 | seq | u32 | monotonico por no (anti-replay) |
| 7 | 4 | ts | u32 | unix time, segundos |
| 11 | 2 | temp | i16 | graus C x 100 |
| 13 | 2 | hum | u16 | % x 100 |
| 15 | 1 | status | u8 | 0 OK, 1 ALERTA, 2 ALARME |
| 16 | 4 | lat | i32 | graus x 1e6, 0x7FFFFFFF = invalido |
| 20 | 4 | lon | i32 | graus x 1e6, 0x7FFFFFFF = invalido |
| 24 | 64 | sig | bytes | ECDSA P-256 sobre SHA-256 do payload, r(32)||s(32) |

## Notas para o firmware
- A assinatura cobre exatamente os 24 bytes do payload, sem o campo sig.
- mbedTLS: `mbedtls_ecdsa_sign` devolve r e s separados (`mbedtls_mpi`); escreva cada um em 32 bytes big-endian com `mbedtls_mpi_write_binary`. Nao use a funcao `_write_signature`, que produz DER.
- Se usar micro-ecc: `uECC_sign` com `uECC_secp256r1()` ja devolve r||s (64 bytes).
- A chave publica (65 bytes, 0x04||X||Y) pode ser exportada com `crypto.public_bytes_raw`.
- Teste de aceite: um pacote gerado pelo firmware deve passar em `Gateway.receive` sem alteracao.
