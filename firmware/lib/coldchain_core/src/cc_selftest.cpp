#include "cc_selftest.h"

#include <stdio.h>
#include <string.h>

#include "../../../test_vectors/vectors.h"
#include "cc_packet.h"
#include "cc_signer.h"

int cc_selftest_run(CcPrintLine print_line) {
  char line[2 * CC_PACKET_LEN + 64];
  int failures = 0;

  uint8_t pub[CC_PUB_LEN];
  if (!cc_public_from_private(TEST_PRIV, pub) || memcmp(pub, TEST_PUB, CC_PUB_LEN) != 0) {
    print_line("ERR,selftest,chave publica derivada difere do vetor");
    failures++;
  }

  for (size_t i = 0; i < TEST_VECTOR_COUNT; i++) {
    const TestVector& v = TEST_VECTORS[i];
    const uint8_t* payload = v.packet;
    const uint8_t* sig = v.packet + CC_PAYLOAD_LEN;

    // 1. O payload montado pelo firmware e identico ao do Python, byte a byte.
    if (v.has_reading) {
      CcReading r = v.reading;
      r.temp_cc = cc_temp_to_centi(v.temp_c);
      r.hum_cp = cc_hum_to_centi(v.hum_pct);
      uint8_t built[CC_PAYLOAD_LEN];
      cc_build_payload(r, built);
      if (memcmp(built, payload, CC_PAYLOAD_LEN) != 0) {
        snprintf(line, sizeof(line), "ERR,selftest,vetor %u: payload difere", (unsigned)i);
        print_line(line);
        failures++;
      }
      CcReading parsed;
      if (!cc_parse_payload(payload, parsed) || parsed.seq != v.reading.seq ||
          parsed.temp_cc != v.reading.temp_cc) {
        snprintf(line, sizeof(line), "ERR,selftest,vetor %u: parse difere", (unsigned)i);
        print_line(line);
        failures++;
      }
    }

    // 2. A verificacao do firmware concorda com o esperado (casos negativos rejeitados).
    bool ok = cc_verify(TEST_PUB, payload, CC_PAYLOAD_LEN, sig);
    snprintf(line, sizeof(line), "VERIFY,%u,%s,%s", (unsigned)i, ok ? "valida" : "invalida",
             ok == v.expect_valid ? "OK" : "FALHA");
    print_line(line);
    if (ok != v.expect_valid) failures++;

    // 3. O firmware assina; o Python deve aceitar a assinatura.
    if (v.expect_valid) {
      uint8_t pkt[CC_PACKET_LEN];
      memcpy(pkt, payload, CC_PAYLOAD_LEN);
      if (!cc_sign(TEST_PRIV, payload, CC_PAYLOAD_LEN, pkt + CC_PAYLOAD_LEN) ||
          !cc_verify(TEST_PUB, pkt, CC_PAYLOAD_LEN, pkt + CC_PAYLOAD_LEN)) {
        snprintf(line, sizeof(line), "ERR,selftest,vetor %u: assinatura falhou", (unsigned)i);
        print_line(line);
        failures++;
        continue;
      }
      strcpy(line, "SIGNED,");
      cc_to_hex(pkt, CC_PACKET_LEN, line + strlen(line));
      print_line(line);
    }
  }

  if (failures == 0) {
    print_line("SELFTEST,OK");
  } else {
    snprintf(line, sizeof(line), "SELFTEST,FALHA,%d", failures);
    print_line(line);
  }
  return failures;
}
