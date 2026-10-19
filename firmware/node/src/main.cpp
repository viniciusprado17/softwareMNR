// Firmware do no sensor (Heltec WiFi LoRa 32 V3).
// Ciclo: LEITURA -> DECISAO -> PACOTE (seq na NVS) -> ASSINA -> MOSTRA -> TRANSMITE -> ESPERA
// Saida serial: linhas INFO,... e TX,<seq>,<hex 88 bytes> (verificaveis com
// tools/check_fw_output.py).
#include <Arduino.h>
#include <esp_system.h>
#include <math.h>
#include <stdarg.h>
#include <string.h>

#include "cc_packet.h"
#include "cc_signer.h"
#include "config.h"
#include "display.h"
#include "pins.h"
#include "radio.h"
#include "sensor.h"
#include "storage.h"

#if __has_include("keys.h")
#include "keys.h"
#else
// Permite compilar (CI) sem a chave. O no se recusa a transmitir com a chave modelo.
#warning "firmware/include/keys.h ausente: rode python tools/provision_node.py --node-id 1"
#include "keys.example.h"
#define KEYS_PLACEHOLDER 1
#endif

#if USE_GPS
#include "gps.h"
#endif

static const uint16_t NODE_ID = KEYS_NODE_ID;
static uint32_t last_sample_ms = 0;
static uint32_t sign_us_mean = 0;
static uint8_t last_status = CC_STATUS_OK;
static bool show_key = false;
static bool key_ok = false;
static TelaNo tela = {};

static int esp_rng(uint8_t* dest, unsigned size) {
  esp_fill_random(dest, size);  // so para mascaramento; o nonce e deterministico
  return 1;
}

static void print_info(const char* fmt, ...) {
  char buf[160];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  Serial.print("INFO,");
  Serial.println(buf);
}

// Medicao obrigatoria (Secao 8.7): n assinaturas, media/min/max/desvio em microssegundos.
static void bench_sign() {
  uint8_t payload[CC_PAYLOAD_LEN] = {CC_VERSION};
  uint8_t sig[CC_SIG_LEN];
  double sum = 0, sum2 = 0;
  uint32_t mn = UINT32_MAX, mx = 0;
  for (int i = 0; i < BENCH_SIGN_N; i++) {
    payload[6] = (uint8_t)i;
    uint32_t t0 = micros();
    cc_sign(NODE_PRIVATE_KEY, payload, sizeof(payload), sig);
    uint32_t dt = micros() - t0;
    sum += dt;
    sum2 += (double)dt * dt;
    mn = dt < mn ? dt : mn;
    mx = dt > mx ? dt : mx;
  }
  double mean = sum / BENCH_SIGN_N;
  double sd = sqrt(sum2 / BENCH_SIGN_N - mean * mean);
  sign_us_mean = (uint32_t)mean;
  print_info("bench_sign_us,n=%d,media=%.0f,min=%lu,max=%lu,desvio=%.0f,cpu_mhz=%lu", BENCH_SIGN_N,
             mean, (unsigned long)mn, (unsigned long)mx, sd, (unsigned long)getCpuFrequencyMhz());
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(300);
  display_begin();
  display_mensagem("MNR 2026 - no sensor", "iniciando...");
  print_info("no=%u fw=node-1.0 freq=%.1fMHz sf=%d intervalo_ms=%lu (artigo: %lu)", NODE_ID,
             LORA_FREQ_MHZ, LORA_SF, (unsigned long)SAMPLE_INTERVAL_MS,
             (unsigned long)SAMPLE_INTERVAL_REF_MS);
  pinMode(BUTTON_PRG, INPUT_PULLUP);
  cc_set_rng(&esp_rng);

  // A chave publica derivada precisa bater com a cadastrada no gateway.
  uint8_t pub[CC_PUB_LEN];
  key_ok = cc_public_from_private(NODE_PRIVATE_KEY, pub) &&
           memcmp(pub, NODE_PUBLIC_KEY, CC_PUB_LEN) == 0;
#ifdef KEYS_PLACEHOLDER
  key_ok = false;
#endif
  if (!key_ok) {
    Serial.println("ERR,chave,keys.h ausente ou inconsistente: nao vou transmitir");
    display_mensagem("ERRO: chave", "rode provision_node", "nao transmite");
  }

  storage_begin();
  print_info("seq_inicial=%lu", (unsigned long)storage_last_seq());

  if (!sensor_begin()) Serial.println("ERR,sensor,SHT31 nao respondeu (tentara de novo)");

  int16_t st = radio_begin();
  if (st != 0) {
    Serial.printf("ERR,%d,radio.begin falhou (TCXO/DIO2? ver Secao 8.5)\n", st);
    display_mensagem("ERRO: radio", "codigo", String(st).c_str());
  } else {
    print_info("radio_ok,airtime_teorico_us=%lu", (unsigned long)radio_time_on_air_us(CC_PACKET_LEN));
  }
#if USE_GPS
  gps_begin();
#endif
  if (BENCH_SIGN_ON_BOOT && key_ok) bench_sign();
  enableLoopWDT();  // watchdog ativo: o loop nunca bloqueia por mais que alguns ms
  last_sample_ms = millis() - SAMPLE_INTERVAL_MS;  // primeira amostra imediata
}

static void ciclo() {
  // LEITURA e DECISAO
  Medida m = sensor_ler();
  CcReading r = {};
  r.node_id = NODE_ID;
  r.ts = 0;  // sem RTC: o gateway grava a hora de recebimento (rx_ts)
  r.lat_e6 = CC_GPS_INVALID;
  r.lon_e6 = CC_GPS_INVALID;
#if USE_GPS
  gps_fill(r);
#endif
  tela.node_id = NODE_ID;
  tela.sensor_ok = m.ok;
  if (!m.ok) {
    Serial.println("ERR,sensor,falha de leitura");
    tela.tx_ok = false;
    display_leitura(tela);
    return;  // sem leitura valida nao ha pacote
  }
  r.temp_cc = cc_temp_to_centi(m.temp_c);
  r.hum_cp = cc_hum_to_centi(m.hum_pct);
  r.status = cc_classify(m.temp_c, TEMP_LOW_C, TEMP_HIGH_C, TEMP_MARGIN_C);
  last_status = r.status;

  // PACOTE: seq gravado na NVS ANTES de transmitir
  if (!key_ok) {
    tela.temp_c = m.temp_c;
    tela.hum_pct = m.hum_pct;
    tela.status = r.status;
    tela.tx_ok = false;
    display_leitura(tela);
    return;
  }
  r.seq = storage_next_seq();
  uint8_t pkt[CC_PACKET_LEN];
  cc_build_payload(r, pkt);

  // ASSINA
  uint32_t t0 = micros();
  bool signed_ok = cc_sign(NODE_PRIVATE_KEY, pkt, CC_PAYLOAD_LEN, pkt + CC_PAYLOAD_LEN);
  uint32_t sign_us = micros() - t0;

  // MOSTRA
  tela.seq = r.seq;
  tela.temp_c = m.temp_c;
  tela.hum_pct = m.hum_pct;
  tela.status = r.status;
  tela.sign_ms = (sign_us + 500) / 1000;

  // TRANSMITE
  int16_t st = -1;
  uint32_t tx_us = 0;
  if (signed_ok) {
    uint32_t t1 = micros();
    st = radio_send(pkt, CC_PACKET_LEN);
    tx_us = micros() - t1;
  }
  tela.tx_ok = st == 0;
  if (!show_key) display_leitura(tela);

  char hex[2 * CC_PACKET_LEN + 1];
  cc_to_hex(pkt, CC_PACKET_LEN, hex);
  Serial.printf("TX,%lu,%s\n", (unsigned long)r.seq, hex);
  print_info("seq=%lu,temp=%.2f,status=%u,sign_us=%lu,tx_us=%lu,radio=%d", (unsigned long)r.seq,
             m.temp_c, r.status, (unsigned long)sign_us, (unsigned long)tx_us, st);
}

void loop() {
  // Botao PRG alterna entre a tela de leitura e a da chave publica.
  static bool btn_prev = true;
  bool btn = digitalRead(BUTTON_PRG);
  if (!btn && btn_prev) {
    show_key = !show_key;
    if (show_key) {
      display_chave(NODE_PUBLIC_KEY, sign_us_mean);
    } else {
      display_leitura(tela);
    }
  }
  btn_prev = btn;

#if USE_GPS
  gps_poll();
#endif
  led_update(last_status);
  if (millis() - last_sample_ms >= SAMPLE_INTERVAL_MS) {
    last_sample_ms += SAMPLE_INTERVAL_MS;
    ciclo();
  }
  delay(10);
}
