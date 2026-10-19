// Abstracao do sensor (Secao 8.4). Qualquer substituto (DS18B20, DHT22) so precisa
// implementar sensor_begin/sensor_ler. Sem umidade: devolver 0 e documentar.
#pragma once

struct Medida {
  float temp_c;
  float hum_pct;
  bool ok;
};

bool sensor_begin();
Medida sensor_ler();
