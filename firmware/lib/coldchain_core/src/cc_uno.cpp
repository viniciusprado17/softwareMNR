#include "cc_uno.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

// strtod/strtof com verificacao: o texto vem por um fio, pode chegar truncado ou com ruido.
static bool read_float(const char* p, char unit, float* v) {
  char* end = nullptr;
  double d = strtod(p, &end);
  if (end == p || isnan(d) || isinf(d)) return false;
  if (unit && *end != unit) return false;
  *v = (float)d;
  return true;
}

static bool read_double(const char* p, double* v) {
  char* end = nullptr;
  double d = strtod(p, &end);
  if (end == p || isnan(d) || isinf(d)) return false;
  *v = d;
  return true;
}

bool cc_parse_uno_line(const char* line, CcUnoLine* out) {
  memset(out, 0, sizeof(*out));
  if (!line) return false;
  const char* t = strstr(line, "T:");
  const char* u = strstr(line, "U:");
  bool erro = strstr(line, "ERRO SHT31") != nullptr;
  if (!t && !erro) return false;  // linha desconhecida (ruido, diagnostico)

  if (t && u && !erro) {
    float tc = NAN, hp = NAN;
    if (read_float(t + 2, 'C', &tc) && read_float(u + 2, '%', &hp) && tc > -40.0f &&
        tc < 125.0f && hp >= 0.0f && hp <= 100.0f) {  // faixa do SHT31
      out->ok = true;
      out->temp_c = tc;
      out->hum_pct = hp;
    }
  }

  const char* la = strstr(line, "LAT:");
  const char* lo = strstr(line, "LON:");
  double lat = 0, lon = 0;
  if (la && lo && read_double(la + 4, &lat) && read_double(lo + 4, &lon) && fabs(lat) <= 90.0 &&
      fabs(lon) <= 180.0) {
    out->has_fix = true;
    out->lat = lat;
    out->lon = lon;
  }
  return true;
}
