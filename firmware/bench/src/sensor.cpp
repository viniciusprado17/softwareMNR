// Bancada, etapas 5 e 6: le o SHT31-D, classifica (mesma regra do no: cc_classify) e mostra
// no display. LED externo acende em ALARME. Sem radio, sem assinatura, sem chaves.
// Serial: SENS,<temp_c>,<hum_pct>,<OK|ALERTA|ALARME> a cada 2 s, ou ERR,sensor.
#include <Adafruit_SHT31.h>
#include <Arduino.h>
#include <Wire.h>

#include "bench_oled.h"
#include "cc_packet.h"
#include "config.h"
#include "pins.h"

static Adafruit_SHT31 sht(&Wire1);
static bool sht_ok = false;
static const char* NAMES[] = {"OK", "ALERTA", "ALARME"};

static bool sensor_start() {
  // 0x44 e o endereco padrao; 0x45 se o pino ADDR estiver em nivel alto
  sht_ok = sht.begin(SHT31_ADDR) || sht.begin(SHT31_ADDR == 0x44 ? 0x45 : 0x44);
  return sht_ok;
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  oled_begin();
  pinMode(ALARM_LED, OUTPUT);
  digitalWrite(ALARM_LED, LOW);
  Wire1.begin(SENSOR_SDA, SENSOR_SCL);
  Wire1.setTimeOut(SENSOR_TIMEOUT_MS);
  Serial.printf("INFO,sensor,sda=%d,scl=%d,sht31=%s\n", SENSOR_SDA, SENSOR_SCL,
                sensor_start() ? "ok" : "ERRO");
}

void loop() {
  float t = NAN, h = NAN;
  if ((!sht_ok && !sensor_start()) || !sht.readBoth(&t, &h) || isnan(t) || isnan(h)) {
    sht_ok = false;
    Serial.println("ERR,sensor");
    oled_show("SENSOR?", "sem resposta", "confira os 4 fios", "e rode o i2cscan");
    digitalWrite(ALARM_LED, LOW);
    delay(2000);
    return;
  }
  uint8_t st = cc_classify(t, TEMP_LOW_C, TEMP_HIGH_C, TEMP_MARGIN_C);
  const char* name = st <= CC_STATUS_ALARM ? NAMES[st] : "?";
  char big[16], l2[24];
  snprintf(big, sizeof(big), "%.2f C", t);
  snprintf(l2, sizeof(l2), "umidade %.0f %%", h);
  oled_show(big, l2, "", name);
  digitalWrite(ALARM_LED, st == CC_STATUS_ALARM ? HIGH : LOW);
  Serial.printf("SENS,%.2f,%.1f,%s\n", t, h, name);
  delay(2000);
}
