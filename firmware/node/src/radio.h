// LoRa ponto a ponto via RadioLib (SX1262). Parametros em include/config.h.
#pragma once

#include <stddef.h>
#include <stdint.h>

// Retorna o codigo de estado do RadioLib (0 = sucesso).
int16_t radio_begin();
int16_t radio_send(const uint8_t* data, size_t len);
// Tempo no ar teorico calculado pelo RadioLib, em microssegundos.
uint32_t radio_time_on_air_us(size_t len);
