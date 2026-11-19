#include "sensor.h"

#include <Arduino.h>

#include "config.h"
#include "pins.h"

#if SENSOR_UNO
// Prototipo montado (manual LACOR MNR, 18/11): o SHT31 e o GPS estao no Arduino Uno, que
// envia a cada ~5 s uma linha "T:25.18C U:62.69% GPS:SEM FIX" a 9600 baud pelo D3. O sinal
// passa por um divisor de tensao (3 x 1 kOhm) e chega ao GPIO41 desta Heltec.
// Aqui so recebemos a linha; a decisao, o pacote e a ASSINATURA continuam nesta Heltec.
// Limite a declarar: o trecho Uno -> Heltec e um fio sem autenticacao.
#include <HardwareSerial.h>

#include "cc_uno.h"

static HardwareSerial uno_serial(1);
static char linha[128];
static size_t pos = 0;
static bool descartando = false;
static CcUnoLine ultima = {};
static uint32_t ultima_ms = 0;
static bool tem_ultima = false;

bool sensor_begin() {
  uno_serial.begin(UNO_BAUD, SERIAL_8N1, UNO_RX_PIN, -1);  // so recebe; nao responde ao Uno
  return true;
}

static void processa_linha() {
  linha[pos] = '\0';
  CcUnoLine r;
  if (!cc_parse_uno_line(linha, &r)) {
    Serial.printf("INFO,uno_ignorada,%s\n", linha);
    return;
  }
  Serial.printf("INFO,uno,%s\n", linha);
  ultima = r;
  ultima_ms = millis();
  tem_ultima = true;
}

void sensor_poll() {
  while (uno_serial.available() > 0) {
    char c = (char)uno_serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (descartando) {
        Serial.println("ERR,uno,linha longa demais; descartada");
      } else if (pos > 0) {
        processa_linha();
      }
      pos = 0;
      descartando = false;
    } else if (!descartando) {
      if (pos < sizeof(linha) - 1) {
        linha[pos++] = c;
      } else {
        descartando = true;
      }
    }
  }
}

Medida sensor_ler() {
  // Leitura velha nao vira pacote: sem linha recente do Uno, o no fica em silencio e o
  // gateway sinaliza "silencio" (e honesto: nao repete a ultima temperatura).
  if (!tem_ultima || millis() - ultima_ms > UNO_MAX_AGE_MS || !ultima.ok) {
    return {NAN, NAN, false, false, 0, 0};
  }
  return {ultima.temp_c, ultima.hum_pct, true, ultima.has_fix, ultima.lat, ultima.lon};
}
#elif SENSOR_FAKE
// Sensor falso (-DSENSOR_FAKE=1): permite testar radio e assinatura antes do SHT31-D chegar.
// A demonstracao deve deixar claro quando este modo estiver em uso.
bool sensor_begin() { return true; }
void sensor_poll() {}

Medida sensor_ler() {
  float t = 5.0f + 4.0f * sinf(millis() / 60000.0f * 2.0f * PI);  // oscila de 1 a 9 C em 1 min
  return {t, 45.0f, true, false, 0, 0};
}
#else
#include <Adafruit_SHT31.h>
#include <Wire.h>

static Adafruit_SHT31 sht(&Wire1);
static bool sht_ok = false;

bool sensor_begin() {
  Wire1.begin(SENSOR_SDA, SENSOR_SCL);
  Wire1.setTimeOut(SENSOR_TIMEOUT_MS);  // o laco nao pode travar esperando o sensor
  sht_ok = sht.begin(SHT31_ADDR);
  return sht_ok;
}

void sensor_poll() {}

Medida sensor_ler() {
  if (!sht_ok && !sensor_begin()) return {NAN, NAN, false, false, 0, 0};
  float t = NAN, h = NAN;
  if (!sht.readBoth(&t, &h) || isnan(t) || isnan(h)) {
    sht_ok = false;  // tenta reinicializar na proxima leitura
    return {NAN, NAN, false, false, 0, 0};
  }
  return {t, h, true, false, 0, 0};
}
#endif
