// OLED integrado (SSD1306 128x64) e LED de alarme (Secao 8.8).
#pragma once

#include <stdint.h>

struct TelaNo {
  uint16_t node_id;
  uint32_t seq;
  float temp_c;
  float hum_pct;
  uint8_t status;
  bool sensor_ok;
  bool tx_ok;
  uint32_t sign_ms;
};

bool display_begin();
void display_mensagem(const char* l1, const char* l2 = "", const char* l3 = "");
void display_leitura(const TelaNo& t);
void display_chave(const uint8_t pub[64], uint32_t sign_us_mean);
// Chamar em todo loop: LED fixo em ALARME, piscando em ALERTA, apagado em OK.
void led_update(uint8_t status);
