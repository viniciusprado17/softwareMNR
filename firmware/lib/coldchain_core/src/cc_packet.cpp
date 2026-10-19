#include "cc_packet.h"

#include <math.h>

static void put_u16(uint8_t* p, uint16_t v) {
  p[0] = (uint8_t)(v >> 8);
  p[1] = (uint8_t)v;
}

static void put_u32(uint8_t* p, uint32_t v) {
  p[0] = (uint8_t)(v >> 24);
  p[1] = (uint8_t)(v >> 16);
  p[2] = (uint8_t)(v >> 8);
  p[3] = (uint8_t)v;
}

static uint16_t get_u16(const uint8_t* p) { return (uint16_t)((p[0] << 8) | p[1]); }

static uint32_t get_u32(const uint8_t* p) {
  return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

int16_t cc_temp_to_centi(float temp_c) {
  long v = lroundf(temp_c * 100.0f);
  if (v > INT16_MAX) v = INT16_MAX;
  if (v < INT16_MIN) v = INT16_MIN;
  return (int16_t)v;
}

uint16_t cc_hum_to_centi(float hum_pct) {
  long v = lroundf(hum_pct * 100.0f);
  if (v < 0) v = 0;
  if (v > UINT16_MAX) v = UINT16_MAX;
  return (uint16_t)v;
}

uint8_t cc_classify(float temp_c, float low, float high, float margin) {
  if (temp_c < low || temp_c > high) return CC_STATUS_ALARM;
  if (temp_c < low + margin || temp_c > high - margin) return CC_STATUS_WARN;
  return CC_STATUS_OK;
}

void cc_build_payload(const CcReading& r, uint8_t out[CC_PAYLOAD_LEN]) {
  out[0] = CC_VERSION;
  put_u16(out + 1, r.node_id);
  put_u32(out + 3, r.seq);
  put_u32(out + 7, r.ts);
  put_u16(out + 11, (uint16_t)r.temp_cc);  // complemento de dois
  put_u16(out + 13, r.hum_cp);
  out[15] = r.status;
  put_u32(out + 16, (uint32_t)r.lat_e6);
  put_u32(out + 20, (uint32_t)r.lon_e6);
}

bool cc_parse_payload(const uint8_t in[CC_PAYLOAD_LEN], CcReading& r) {
  if (in[0] != CC_VERSION || in[15] > CC_STATUS_ALARM) return false;
  r.node_id = get_u16(in + 1);
  r.seq = get_u32(in + 3);
  r.ts = get_u32(in + 7);
  r.temp_cc = (int16_t)get_u16(in + 11);
  r.hum_cp = get_u16(in + 13);
  r.status = in[15];
  r.lat_e6 = (int32_t)get_u32(in + 16);
  r.lon_e6 = (int32_t)get_u32(in + 20);
  return true;
}

void cc_to_hex(const uint8_t* data, size_t len, char* out) {
  static const char digits[] = "0123456789abcdef";
  for (size_t i = 0; i < len; i++) {
    out[2 * i] = digits[data[i] >> 4];
    out[2 * i + 1] = digits[data[i] & 0x0F];
  }
  out[2 * len] = '\0';
}

static int hex_nibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

bool cc_from_hex(const char* hex, uint8_t* out, size_t len) {
  for (size_t i = 0; i < len; i++) {
    int hi = hex_nibble(hex[2 * i]);
    int lo = hex_nibble(hex[2 * i + 1]);
    if (hi < 0 || lo < 0) return false;
    out[i] = (uint8_t)((hi << 4) | lo);
  }
  return true;
}
