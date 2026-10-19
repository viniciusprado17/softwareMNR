#include "gps.h"

#if USE_GPS
#include <Arduino.h>
#include <TinyGPSPlus.h>

#include "pins.h"

static TinyGPSPlus gps;
static HardwareSerial gps_serial(1);

// Dias desde 1970-01-01 (algoritmo days_from_civil, H. Hinnant).
static int32_t days_from_civil(int32_t y, uint32_t m, uint32_t d) {
  y -= m <= 2;
  const int32_t era = (y >= 0 ? y : y - 399) / 400;
  const uint32_t yoe = (uint32_t)(y - era * 400);
  const uint32_t doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const uint32_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return era * 146097 + (int32_t)doe - 719468;
}

void gps_begin() { gps_serial.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX); }

void gps_poll() {
  while (gps_serial.available()) gps.encode(gps_serial.read());
}

bool gps_has_fix() { return gps.location.isValid() && gps.location.age() < 5000; }

void gps_fill(CcReading& r) {
  if (gps_has_fix()) {
    r.lat_e6 = (int32_t)lround(gps.location.lat() * 1e6);
    r.lon_e6 = (int32_t)lround(gps.location.lng() * 1e6);
  }
  if (gps.date.isValid() && gps.time.isValid() && gps.date.year() >= 2024) {
    int32_t days = days_from_civil(gps.date.year(), gps.date.month(), gps.date.day());
    r.ts = (uint32_t)days * 86400u + gps.time.hour() * 3600u + gps.time.minute() * 60u +
           gps.time.second();
  }
}
#endif
