// Autoteste com os vetores dourados. Roda igual no ESP32 (firmware/vectest) e no PC
// (firmware/test_host), para provar que firmware e Python falam a mesma lingua (Secao 12.2).
#pragma once

#include <stddef.h>

// Funcao de saida de linha (Serial.println no ESP32, puts no PC).
typedef void (*CcPrintLine)(const char* line);

// T4: confere montagem do payload e verificacao de todos os vetores.
// T5: assina cada payload valido com a chave de teste e imprime "SIGNED,<hex 88 bytes>",
//     para o Python verificar (tools/check_fw_output.py).
// Retorna o numero de falhas (0 = tudo OK). Imprime "SELFTEST,OK" ou "SELFTEST,FALHA,<n>".
int cc_selftest_run(CcPrintLine print_line);
