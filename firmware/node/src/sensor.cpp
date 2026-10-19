#include "sensor.h"

#include <Arduino.h>

#include "config.h"
#include "pins.h"

#if SENSOR_FAKE
// Sensor falso (-DSENSOR_FAKE=1): permite testar radio e assinatura antes do SHT31-D chegar.
// A demonstracao deve deixar claro quando este modo estiver em uso.
bool sensor_begin() { return true; }

Medida sensor_ler() {
  float t = 5.0f + 4.0f * sinf(millis() / 60000.0f * 2.0f * PI);  // oscila de 1 a 9 C em 1 min
  return {t, 45.0f, true};
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

Medida sensor_ler() {
  if (!sht_ok && !sensor_begin()) return {NAN, NAN, false};
  float t = NAN, h = NAN;
  if (!sht.readBoth(&t, &h) || isnan(t) || isnan(h)) {
    sht_ok = false;  // tenta reinicializar na proxima leitura
    return {NAN, NAN, false};
  }
  return {t, h, true};
}
#endif
