// Interpreta a linha de texto que o Arduino Uno do prototipo envia a Heltec transmissora
// (sketch MNR_Uno, 9600 baud pelo divisor no GPIO41). Formatos aceitos:
//   "T:25.18C U:62.69% GPS:SEM FIX"
//   "T:25.18C U:62.69% LAT:-10.947200 LON:-37.073100"
//   "ERRO SHT31 GPS:SEM FIX"            (sensor falhou: leitura invalida)
// Portatil (sem Arduino): compila no ESP32 e no PC (firmware/test_host).
#pragma once
#include <stdbool.h>

typedef struct {
  bool ok;        // temperatura e umidade validas
  float temp_c;
  float hum_pct;
  bool has_fix;   // LAT e LON presentes
  double lat;
  double lon;
} CcUnoLine;

// Devolve true se a linha foi reconhecida (com ou sem leitura valida).
bool cc_parse_uno_line(const char* line, CcUnoLine* out);
