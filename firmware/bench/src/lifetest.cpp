// Bancada, etapa 4 (teste de vida): display mostra texto e o LED da placa pisca.
// Serial: LIFE,<segundos> a cada 1 s. Nao usa radio, sensor nem chaves.
#include <Arduino.h>

#include "bench_oled.h"
#include "config.h"
#include "pins.h"

static uint32_t seconds = 0;

void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(BOARD_LED, OUTPUT);
  bool ok = oled_begin();
  Serial.printf("INFO,lifetest,oled=%s\n", ok ? "ok" : "ERRO");
}

void loop() {
  char line[24];
  snprintf(line, sizeof(line), "%lu s", (unsigned long)seconds);
  oled_show("VIVO", line, "Heltec V3", "teste de vida");
  digitalWrite(BOARD_LED, seconds % 2 ? HIGH : LOW);
  Serial.printf("LIFE,%lu\n", (unsigned long)seconds);
  seconds++;
  delay(1000);
}
