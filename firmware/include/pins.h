// Todos os pinos do projeto, num unico lugar (Secao 5).
// Valores USUAIS da Heltec WiFi LoRa 32 V3. CONFIRMAR no pinout oficial da revisao da placa
// antes de ligar qualquer fio.
#pragma once

// ---- Radio SX1262 (interno) ----
#define LORA_NSS 8
#define LORA_SCK 9
#define LORA_MOSI 10
#define LORA_MISO 11
#define LORA_RST 12
#define LORA_BUSY 13
#define LORA_DIO1 14

// ---- OLED SSD1306 128x64 (interno, ocupa o I2C padrao: Wire) ----
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21
#define OLED_ADDR 0x3C

// ---- Placa ----
#define VEXT_CTRL 36  // nivel BAIXO liga a alimentacao dos perifericos (o OLED depende dele)
#define BOARD_LED 35  // LED branco da placa
#define BUTTON_PRG 0

// ---- SHT31-D no segundo barramento I2C (Wire1). CONFIRMAR que estao livres no header ----
#define SENSOR_SDA 41
#define SENSOR_SCL 42
#define SHT31_ADDR 0x44  // 0x45 se o pino ADDR estiver em nivel alto

// ---- LED de alarme externo: anodo -> resistor 220 ohm -> GPIO; catodo no GND ----
#define ALARM_LED 4

// ---- GPS NEO-6M (Camada 3, opcional). Evitar GPIO 19 e 20 (USB nativa do ESP32-S3) ----
#define GPS_RX 47  // RX do ESP32 <- TX do GPS
#define GPS_TX 48  // TX do ESP32 -> RX do GPS
