// GPS NEO-6M (Camada 3, opcional; compilar com -DUSE_GPS=1). Sem fix, lat/lon ficam
// invalidos (0x7FFFFFFF) e ts = 0. Nunca depender dele na demonstracao.
#pragma once

#include "cc_packet.h"

void gps_begin();
void gps_poll();  // chamar em todo loop: consome os bytes NMEA da UART
void gps_fill(CcReading& r);
bool gps_has_fix();
