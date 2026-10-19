// Formato binario do pacote v1. Espelho byte a byte de src/coldchain/packet.py.
// Big-endian. Payload de 24 bytes + assinatura r||s de 64 bytes = 88 bytes.
#pragma once

#include <stddef.h>
#include <stdint.h>

#define CC_VERSION 1
#define CC_PAYLOAD_LEN 24
#define CC_SIG_LEN 64
#define CC_PACKET_LEN (CC_PAYLOAD_LEN + CC_SIG_LEN)
#define CC_GPS_INVALID 0x7FFFFFFF

enum CcStatus : uint8_t { CC_STATUS_OK = 0, CC_STATUS_WARN = 1, CC_STATUS_ALARM = 2 };

struct CcReading {
  uint16_t node_id;
  uint32_t seq;
  uint32_t ts;      // unix time em segundos, 0 = desconhecido
  int16_t temp_cc;  // centesimos de grau C
  uint16_t hum_cp;  // centesimos de %
  uint8_t status;
  int32_t lat_e6;   // graus * 1e6, CC_GPS_INVALID sem fix
  int32_t lon_e6;
};

// Conversoes com arredondamento igual ao do Python (round(x * 100)).
int16_t cc_temp_to_centi(float temp_c);
uint16_t cc_hum_to_centi(float hum_pct);

// Classificacao termica (mesma regra de src/coldchain/decision.py).
uint8_t cc_classify(float temp_c, float low, float high, float margin);

// Monta os 24 bytes do payload.
void cc_build_payload(const CcReading& r, uint8_t out[CC_PAYLOAD_LEN]);

// Decodifica 24 bytes. Retorna false se versao ou status forem invalidos.
bool cc_parse_payload(const uint8_t in[CC_PAYLOAD_LEN], CcReading& r);

// Escreve `len` bytes como hex minusculo em `out` (precisa de 2*len+1 bytes).
void cc_to_hex(const uint8_t* data, size_t len, char* out);

// Le hex (2*len caracteres) para bytes. Retorna false se houver caractere invalido.
bool cc_from_hex(const char* hex, uint8_t* out, size_t len);
