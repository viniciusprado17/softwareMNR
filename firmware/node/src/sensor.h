// Abstracao do sensor (Secao 8.4). Qualquer substituto (DS18B20, DHT22) so precisa
// implementar sensor_begin/sensor_ler. Sem umidade: devolver 0 e documentar.
#pragma once

struct Medida {
  float temp_c;
  float hum_pct;
  bool ok;
  bool has_fix;  // so no modo SENSOR_UNO: posicao do GPS que o Uno repassou
  double lat;
  double lon;
};

bool sensor_begin();
Medida sensor_ler();
// Chamado a cada volta do loop (no modo SENSOR_UNO le a serial do Uno; nos outros, nada).
void sensor_poll();
