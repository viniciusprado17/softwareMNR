# Registro de decisões técnicas

Cada decisão que muda contrato (pacote, serial, API), dependência ou escopo entra aqui com data e motivo.

| Data | Decisão | Motivo | Consequência |
|---|---|---|---|
| 19/10/2026 | Curva **P-256** (secp256r1) **confirmada** pelo Vini (issue #9) | Padrão NIST usado em IoT; compatível com elementos seguros (ATECC608 só faz P-256) e com o AWS IoT Core; já implementada e testada em Python, vetores e firmware. A secp256k1 do artigo foi usada só na simulação em Python | Não é conflito: é adaptação/evolução do protótipo, declarada como em `docs/ARTIGO_X_DEMONSTRACAO.md`. Se um dia trocar: `CURVE` em `crypto.py`, `uECC_secp256r1()` e `uECC_SUPPORTS_*` no firmware, regenerar vetores e reprovisionar chaves |
| 19/10/2026 | Firmware assina com **micro-ecc** (`uECC_sign_deterministic`), não com mbedTLS | A API do mbedTLS muda entre o core 2.x e 3.x; a micro-ecc já entrega r‖s de 64 bytes e é a biblioteca citada no artigo. Nonce determinístico evita depender do RNG do ESP32 | Mesma biblioteca roda no PC: `firmware/test_host` prova a interoperabilidade antes da placa chegar |
| 19/10/2026 | SHA-256 próprio (`cc_sha256.cpp`) no firmware | Mesmo motivo (independe da versão do mbedTLS) e permite teste no PC | Conferido com vetores FIPS 180-2 no teste do PC |
| 19/10/2026 | Versões fixadas: espressif32 6.9.0 (Arduino-ESP32 2.0.17), RadioLib 6.6.0, micro-ecc commit `541b3a7` (cópia local) | Reprodutibilidade (Seção 7.4, item 1) | Atualizar só com teste em placa |
| 19/10/2026 | Ledger: colunas de conveniência (`rx_ts`, `rssi`, `snr`, `temp_c`, `status`, `anomaly`, `kind`) fora do hash; tabela `events` para rejeições | Seção 10.2 | `verify_chain(keys)` reconfere hash, assinatura e colunas, e devolve `{ok, bloco, motivo}`. Bancos antigos são migrados automaticamente |
| 19/10/2026 | Ressincronização (`--reset-node`) como bloco especial `kind=resync` dentro da corrente | Seção 8.6; fica auditável no ledger | Desligada por padrão (`allow_resync = false`) |
| 19/10/2026 | Porta serial padrão `/dev/ttyUSB0` | A Heltec V3 usa ponte CP2102 | Ajustável em `config.toml` ou `--port` |
| 19/10/2026 | Tela consulta a API a cada 1 s (sem WebSocket) e desenha o gráfico em canvas próprio | "Prefira o simples" (Seção 10.5); sem CDN (Wi-Fi ruim no evento) | Nenhum arquivo externo |
| 19/10/2026 | micro-ecc copiada para `firmware/lib/coldchain_core/src/uecc/` com símbolos renomeados para `cc_uECC_*` | O `libbt` do ESP-IDF embute o tinycrypt com os mesmos nomes (`uECC_sign`, `uECC_verify`...): o linker acusava "multiple definition" no CI | `cc_uecc_rename.h` + `cc_uecc.c`; só a curva secp256r1 é compilada. Para trocar de curva, ajustar também `uECC_SUPPORTS_*` nesse header |
