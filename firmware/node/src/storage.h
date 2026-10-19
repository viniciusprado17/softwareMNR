// Contador seq persistente na NVS (Secao 8.6): sobrevive a reinicio, evitando falso replay.
#pragma once

#include <stdint.h>

void storage_begin();
uint32_t storage_last_seq();
// Incrementa e GRAVA antes de transmitir. Reinicio entre gravar e transmitir so pula um
// numero (aceitavel); o inverso causaria seq repetido e rejeicao como replay.
uint32_t storage_next_seq();
