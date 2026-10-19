// Firmware de teste dos vetores dourados (testes T4 e T5, tarefa B3). Rodar ANTES de ligar
// o radio. Saida: VERIFY,..., SIGNED,<hex> e SELFTEST,OK. Conferir no PC com:
//   python tools/check_fw_output.py --vectors --port /dev/ttyUSB0 --seconds 15
#include <Arduino.h>
#include <math.h>

#include "cc_packet.h"
#include "cc_selftest.h"
#include "cc_signer.h"
#include "config.h"
#include "../../test_vectors/vectors.h"

static void print_line(const char* line) { Serial.println(line); }

static void bench(const char* name, bool sign) {
  uint8_t sig[CC_SIG_LEN];
  const uint8_t* payload = TEST_VECTORS[0].packet;
  double sum = 0, sum2 = 0;
  uint32_t mn = UINT32_MAX, mx = 0;
  for (int i = 0; i < BENCH_SIGN_N; i++) {
    uint32_t t0 = micros();
    if (sign) {
      cc_sign(TEST_PRIV, payload, CC_PAYLOAD_LEN, sig);
    } else {
      cc_verify(TEST_PUB, payload, CC_PAYLOAD_LEN, payload + CC_PAYLOAD_LEN);
    }
    uint32_t dt = micros() - t0;
    sum += dt;
    sum2 += (double)dt * dt;
    mn = dt < mn ? dt : mn;
    mx = dt > mx ? dt : mx;
  }
  double mean = sum / BENCH_SIGN_N;
  Serial.printf("INFO,bench_%s_us,n=%d,media=%.0f,min=%lu,max=%lu,desvio=%.0f,cpu_mhz=%lu\n", name,
                BENCH_SIGN_N, mean, (unsigned long)mn, (unsigned long)mx,
                sqrt(sum2 / BENCH_SIGN_N - mean * mean), (unsigned long)getCpuFrequencyMhz());
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1500);  // tempo para abrir o monitor serial
}

void loop() {
  Serial.println("INFO,vectest fw=vectest-1.0");
  cc_selftest_run(print_line);
  bench("sign", true);
  bench("verify", false);
  delay(10000);  // repete a cada 10 s
}
