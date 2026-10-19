// Firmware do receptor (Heltec WiFi LoRa 32 V3): ouve o radio e repassa cada pacote a USB.
// NAO verifica assinatura nem decide nada (Secao 4.2). Protocolo serial (Secao 9.3):
//   RX,<rssi>,<snr>,<hex>   INFO,<texto>   ERR,<codigo>,<texto>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <Wire.h>

#include "cc_packet.h"
#include "config.h"
#include "pins.h"

static SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);
static Adafruit_SSD1306 oled(128, 64, &Wire, OLED_RST);
static bool oled_ok = false;
static volatile bool received = false;
static uint32_t count = 0, crc_errors = 0;

static void IRAM_ATTR on_packet() { received = true; }

static void tela(const char* l1, const char* l2 = "", const char* l3 = "") {
  if (!oled_ok) return;
  oled.clearDisplay();
  oled.setCursor(0, 0);
  oled.println("RECEPTOR LoRa");
  oled.println(l1);
  oled.println(l2);
  oled.println(l3);
  oled.display();
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(300);
  pinMode(VEXT_CTRL, OUTPUT);
  digitalWrite(VEXT_CTRL, LOW);
  delay(50);
  Wire.begin(OLED_SDA, OLED_SCL);
  oled_ok = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  if (oled_ok) oled.setTextColor(SSD1306_WHITE);

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
  int16_t st = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR, LORA_SYNC_WORD,
                           LORA_POWER_DBM, LORA_PREAMBLE, LORA_TCXO_V, false);
  if (st == RADIOLIB_ERR_NONE) st = radio.setDio2AsRfSwitch(true);
  if (st == RADIOLIB_ERR_NONE) st = radio.setCRC(2);
  if (st != RADIOLIB_ERR_NONE) {
    Serial.printf("ERR,%d,radio.begin falhou (TCXO/DIO2? ver Secao 8.5)\n", st);
    tela("ERRO no radio", String(st).c_str());
    return;
  }
  radio.setPacketReceivedAction(on_packet);
  st = radio.startReceive();
  Serial.printf("INFO,receptor fw=receiver-1.0 %.1fMHz SF%d BW%.0f CR4/%d sync=0x%02X st=%d\n",
                LORA_FREQ_MHZ, LORA_SF, LORA_BW_KHZ, LORA_CR, LORA_SYNC_WORD, st);
  tela("ouvindo...", "915 MHz");
}

void loop() {
  if (!received) {
    delay(2);
    return;
  }
  received = false;
  uint8_t buf[256];
  size_t len = radio.getPacketLength();
  if (len > sizeof(buf)) len = sizeof(buf);
  int16_t st = radio.readData(buf, len);
  if (st == RADIOLIB_ERR_NONE) {
    // Imprime mesmo se len != 88: o gateway rejeita com tamanho_invalido (diagnostico).
    char hex[2 * sizeof(buf) + 1];
    cc_to_hex(buf, len, hex);
    float rssi = radio.getRSSI();
    float snr = radio.getSNR();
    Serial.printf("RX,%d,%.1f,%s\n", (int)lroundf(rssi), snr, hex);
    count++;
    char l1[24], l2[24];
    snprintf(l1, sizeof(l1), "pacotes: %lu", (unsigned long)count);
    snprintf(l2, sizeof(l2), "%.0fdBm SNR %.1f", rssi, snr);
    tela(l1, l2, len == CC_PACKET_LEN ? "88 bytes" : "TAMANHO ERRADO");
  } else if (st == RADIOLIB_ERR_CRC_MISMATCH) {
    crc_errors++;
    Serial.printf("ERR,%d,crc invalido (total %lu)\n", st, (unsigned long)crc_errors);
  } else {
    Serial.printf("ERR,%d,falha ao ler pacote\n", st);
  }
  radio.startReceive();
}
