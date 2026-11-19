// Testes do interpretador da linha do Uno (cc_uno). Uso: bash firmware/test_host/run.sh
#include <math.h>
#include <stdio.h>

#include "cc_uno.h"

static int fails = 0;
#define CHECK(c)                                          \
  do {                                                    \
    if (!(c)) {                                           \
      printf("UNO FALHA linha %d: %s\n", __LINE__, #c);   \
      fails++;                                            \
    }                                                     \
  } while (0)

int main() {
  CcUnoLine r;
  CHECK(cc_parse_uno_line("T:25.18C U:62.69% GPS:SEM FIX", &r));
  CHECK(r.ok && fabsf(r.temp_c - 25.18f) < 1e-3f && fabsf(r.hum_pct - 62.69f) < 1e-3f);
  CHECK(!r.has_fix);

  CHECK(cc_parse_uno_line("T:4.50C U:40.00% LAT:-10.947200 LON:-37.073100", &r));
  CHECK(r.ok && r.has_fix && fabs(r.lat + 10.9472) < 1e-6 && fabs(r.lon + 37.0731) < 1e-6);

  CHECK(cc_parse_uno_line("T:-2.25C U:80.10%", &r) && r.ok && fabsf(r.temp_c + 2.25f) < 1e-3f);

  CHECK(cc_parse_uno_line("ERRO SHT31 GPS:SEM FIX", &r) && !r.ok);
  CHECK(cc_parse_uno_line("T:25.1", &r) && !r.ok);           // truncada
  CHECK(cc_parse_uno_line("T:abcC U:50%", &r) && !r.ok);      // lixo
  CHECK(cc_parse_uno_line("T:25.00C U:150.00%", &r) && !r.ok);  // fora da faixa
  CHECK(!cc_parse_uno_line("Caracteres recebidos do GPS: 10", &r));
  CHECK(!cc_parse_uno_line("", &r));

  printf(fails ? "UNO,FALHOU,%d\n" : "UNO,OK,%d\n", fails);
  return fails ? 1 : 0;
}
