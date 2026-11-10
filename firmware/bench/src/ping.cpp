// Bancada, etapa 7: radio entre as duas placas, sem assinatura e sem chaves.
// -DPING_TX=1: envia "PING,<n>" a cada 2 s (Serial: TX,<n>).
// -DPING_TX=0: recebe e mostra (Serial: RX,<rssi>,<snr>,<texto>).
// Mesmos parametros de radio do no e do receptor (include/config.h). ANTENA CONECTADA antes de ligar.
#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>

#include "bench_oled.h"
#include "config.h"
#include "pins.h"

static SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);
static bool radio_ok = false;
static uint32_t counter = 0;

static int16_t radio_start() {
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
  int16_t st = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR, LORA_SYNC_WORD,
                           LORA_POWER_DBM, LORA_PREAMBLE, LORA_TCXO_V, false);
  if (st != RADIOLIB_ERR_NONE) return st;
  st = radio.setDio2AsRfSwitch(true);  // chave RF da Heltec V3 controlada pelo DIO2
  if (st != RADIOLIB_ERR_NONE) return st;
  return radio.setCRC(2);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  oled_begin();
  int16_t st = radio_start();
  radio_ok = st == RADIOLIB_ERR_NONE;
  Serial.printf("INFO,ping_%s,freq=%.1f,sf=%d,radio=%d\n", PING_TX ? "tx" : "rx", (double)LORA_FREQ_MHZ,
                LORA_SF, st);
  if (!radio_ok) {
    char code[20];
    snprintf(code, sizeof(code), "codigo %d", st);
    Serial.printf("ERR,radio,%d\n", st);
    oled_show("RADIO?", code, "ver TCXO/antena", "");
  }
}

void loop() {
  if (!radio_ok) {
    delay(1000);
    return;
  }
#if PING_TX
  char msg[24];
  snprintf(msg, sizeof(msg), "PING,%lu", (unsigned long)counter);
  int16_t st = radio.transmit((uint8_t*)msg, strlen(msg));
  char l2[24];
  snprintf(l2, sizeof(l2), "n = %lu", (unsigned long)counter);
  if (st == RADIOLIB_ERR_NONE) {
    Serial.printf("TX,%lu\n", (unsigned long)counter);
    oled_show("TX", l2, "915 MHz", "enviando PING");
  } else {
    Serial.printf("ERR,radio,%d\n", st);
    oled_show("TX ERRO", l2, "", "");
  }
  counter++;
  delay(2000);
#else
  uint8_t buf[64];
  int16_t st = radio.receive(buf, sizeof(buf) - 1);  // bloqueia ate chegar pacote ou estourar o tempo
  if (st == RADIOLIB_ERR_NONE) {
    size_t n = radio.getPacketLength();
    if (n > sizeof(buf) - 1) n = sizeof(buf) - 1;
    buf[n] = 0;
    float rssi = radio.getRSSI(), snr = radio.getSNR();
    char l2[24], l3[24];
    snprintf(l2, sizeof(l2), "RSSI %.0f dBm", rssi);
    snprintf(l3, sizeof(l3), "SNR %.1f dB", snr);
    Serial.printf("RX,%.0f,%.1f,%s\n", rssi, snr, (char*)buf);
    oled_show("RX", (char*)buf, l2, l3);
    counter++;
  } else if (st != RADIOLIB_ERR_RX_TIMEOUT) {
    Serial.printf("ERR,radio,%d\n", st);
  }
#endif
}
