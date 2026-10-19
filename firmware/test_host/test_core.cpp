// Teste do nucleo do firmware no PC (sem ESP32): pacote, SHA-256 e ECDSA com micro-ecc.
// Compilar e rodar: bash firmware/test_host/run.sh
#include <stdio.h>
#include <string.h>

#include "cc_packet.h"
#include "cc_selftest.h"
#include "cc_sha256.h"

static void print_line(const char* line) { puts(line); }

static int test_sha256() {
  // Vetores do FIPS 180-2: "abc" e mensagem de 2 blocos.
  struct {
    const char* msg;
    const char* hex;
  } cases[] = {
      {"abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"},
      {"", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
      {"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
       "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"},
  };
  int failures = 0;
  for (auto& c : cases) {
    uint8_t out[32];
    char hex[65];
    cc_sha256((const uint8_t*)c.msg, strlen(c.msg), out);
    cc_to_hex(out, 32, hex);
    if (strcmp(hex, c.hex) != 0) {
      printf("ERR,sha256,'%s' -> %s\n", c.msg, hex);
      failures++;
    }
  }
  return failures;
}

static int test_classify() {
  // Mesmos casos de tests/test_coldchain.py::DecisionTests
  struct {
    float t;
    uint8_t expect;
  } cases[] = {{5.0f, 0}, {7.8f, 1}, {2.3f, 1}, {8.1f, 2}, {1.9f, 2}, {8.0f, 1}};
  int failures = 0;
  for (auto& c : cases) {
    if (cc_classify(c.t, 2.0f, 8.0f, 0.5f) != c.expect) {
      printf("ERR,classify,%.2f\n", c.t);
      failures++;
    }
  }
  return failures;
}

int main() {
  int failures = test_sha256() + test_classify();
  failures += cc_selftest_run(print_line);
  printf("HOST,%s\n", failures ? "FALHA" : "OK");
  return failures ? 1 : 0;
}
