// Parametros compartilhados por no e receptor. Os parametros de radio PRECISAM ser identicos
// nos dois lados, por isso ficam so aqui (Secao 8.5).
#pragma once

// ---- Radio LoRa ponto a ponto ----
#ifndef LORA_FREQ_MHZ
#define LORA_FREQ_MHZ 915.0  // faixa do Brasil (915 a 928 MHz)
#endif
#define LORA_BW_KHZ 125.0
#ifndef LORA_SF
#define LORA_SF 7  // 7 na demonstracao, 9 em testes de alcance
#endif
#define LORA_CR 5  // coding rate 4/5
#define LORA_SYNC_WORD 0x12  // rede privada
#define LORA_POWER_DBM 14  // aumentar so se necessario (limites da Anatel)
#define LORA_PREAMBLE 8
// TCXO do SX1262 alimentado pelo DIO3. Heltec V3: 1,8 V (ver exemplos oficiais/RadioLib).
// Se radio.begin() retornar erro, este e o primeiro suspeito (Secao 8.5).
#define LORA_TCXO_V 1.8f

// ---- Amostragem ----
#define SAMPLE_INTERVAL_REF_MS 60000UL  // referencia do artigo: ciclo de 60 s
#ifndef SAMPLE_INTERVAL_MS
#define SAMPLE_INTERVAL_MS 10000UL  // padrao de bancada: 10 s (declarar na demonstracao)
#endif

// ---- Faixa termica (mesma do gateway: config.toml [thresholds]) ----
#define TEMP_LOW_C 2.0f
#define TEMP_HIGH_C 8.0f
#define TEMP_MARGIN_C 0.5f

// ---- Diagnostico ----
#ifndef BENCH_SIGN_ON_BOOT
#define BENCH_SIGN_ON_BOOT 1  // mede o tempo de assinatura (n = BENCH_SIGN_N) ao ligar
#endif
#define BENCH_SIGN_N 100
#define SENSOR_TIMEOUT_MS 500
#define SERIAL_BAUD 115200
