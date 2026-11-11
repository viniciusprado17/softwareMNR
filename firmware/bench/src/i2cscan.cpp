// Bancada, etapa 5: varre o barramento I2C do sensor (Wire1) e lista os enderecos.
// Serial: I2C,found,0x44 por endereco, ou I2C,none. SHT31-D responde em 0x44 (ou 0x45).
// Comando pela serial: "scan <sda> <scl>" troca os pinos e varre de novo (use os pinos
// conferidos no pinout oficial da sua placa; pinos ja ocupados sao recusados).
#include <Arduino.h>
#include <Wire.h>

#include "bench_oled.h"
#include "config.h"
#include "pins.h"

static int sda_pin = SENSOR_SDA;
static int scl_pin = SENSOR_SCL;
static uint32_t last_scan_ms = 0;

// Pinos que nao podem virar I2C do sensor: radio, OLED, Vext, LED, botao e USB nativa.
static bool pin_reserved(int p) {
  static const int used[] = {LORA_NSS, LORA_SCK, LORA_MOSI, LORA_MISO, LORA_RST, LORA_BUSY, LORA_DIO1,
                             OLED_SDA, OLED_SCL, OLED_RST, VEXT_CTRL, BOARD_LED, BUTTON_PRG, 19, 20};
  for (int u : used) {
    if (p == u) return true;
  }
  return p < 0 || p > 48;
}

static void scan() {
  char found[40] = "";
  int n = 0;
  for (uint8_t addr = 0x08; addr <= 0x77; addr++) {
    Wire1.beginTransmission(addr);
    if (Wire1.endTransmission() == 0) {
      Serial.printf("I2C,found,0x%02X\n", addr);
      if (strlen(found) < sizeof(found) - 6) {
        snprintf(found + strlen(found), sizeof(found) - strlen(found), "0x%02X ", addr);
      }
      n++;
    }
  }
  if (n == 0) Serial.println("I2C,none");
  char pins[24];
  snprintf(pins, sizeof(pins), "SDA %d  SCL %d", sda_pin, scl_pin);
  oled_show(n ? "ACHOU" : "NADA", pins, n ? found : "confira os fios", "SHT31 = 0x44/0x45");
}

static void start_bus() {
  Wire1.end();
  Wire1.begin(sda_pin, scl_pin);
  Wire1.setTimeOut(SENSOR_TIMEOUT_MS);
  Serial.printf("INFO,i2cscan,sda=%d,scl=%d\n", sda_pin, scl_pin);
}

static void handle_command() {
  String line = Serial.readStringUntil('\n');
  line.trim();
  int sda = -1, scl = -1;
  if (sscanf(line.c_str(), "scan %d %d", &sda, &scl) != 2) {
    Serial.println("ERR,cmd,use: scan <sda> <scl>");
    return;
  }
  if (sda == scl || pin_reserved(sda) || pin_reserved(scl)) {
    Serial.println("ERR,cmd,pino reservado ou invalido");
    return;
  }
  sda_pin = sda;
  scl_pin = scl;
  start_bus();
  last_scan_ms = 0;
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  Serial.setTimeout(200);
  oled_begin();
  start_bus();
}

void loop() {
  if (Serial.available()) handle_command();
  if (last_scan_ms == 0 || millis() - last_scan_ms >= 3000) {
    last_scan_ms = millis() | 1;
    scan();
  }
}
