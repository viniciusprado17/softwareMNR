#include "radio.h"

#include <RadioLib.h>
#include <SPI.h>

#include "config.h"
#include "pins.h"

static SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);

int16_t radio_begin() {
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
  int16_t st = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR, LORA_SYNC_WORD,
                           LORA_POWER_DBM, LORA_PREAMBLE, LORA_TCXO_V, false);
  if (st != RADIOLIB_ERR_NONE) return st;
  st = radio.setDio2AsRfSwitch(true);  // chave RF da Heltec V3 controlada pelo DIO2
  if (st != RADIOLIB_ERR_NONE) return st;
  return radio.setCRC(2);  // CRC ligado: descarta pacotes corrompidos no radio
}

int16_t radio_send(const uint8_t* data, size_t len) {
  return radio.transmit(const_cast<uint8_t*>(data), len);
}

uint32_t radio_time_on_air_us(size_t len) { return radio.getTimeOnAir(len); }
