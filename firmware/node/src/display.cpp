#include "display.h"

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino.h>
#include <Wire.h>

#include "cc_packet.h"
#include "pins.h"

static Adafruit_SSD1306 oled(128, 64, &Wire, OLED_RST);
static bool oled_ok = false;
static const char* NOMES[] = {"OK", "ALERTA", "ALARME"};

bool display_begin() {
  pinMode(VEXT_CTRL, OUTPUT);
  digitalWrite(VEXT_CTRL, LOW);  // liga Vext (alimenta o OLED)
  delay(50);
  pinMode(ALARM_LED, OUTPUT);
  digitalWrite(ALARM_LED, LOW);
  Wire.begin(OLED_SDA, OLED_SCL);
  oled_ok = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  if (oled_ok) {
    oled.setTextColor(SSD1306_WHITE);
    oled.setTextSize(1);
  }
  return oled_ok;
}

void display_mensagem(const char* l1, const char* l2, const char* l3) {
  if (!oled_ok) return;
  oled.clearDisplay();
  oled.setCursor(0, 0);
  oled.println(l1);
  oled.println(l2);
  oled.println(l3);
  oled.display();
}

void display_leitura(const TelaNo& t) {
  if (!oled_ok) return;
  oled.clearDisplay();
  oled.setCursor(0, 0);
  oled.printf("NO %u   seq %lu\n", t.node_id, (unsigned long)t.seq);
  if (t.sensor_ok) {
    oled.printf("T %.2f C  U %.0f%%\n", t.temp_c, t.hum_pct);
  } else {
    oled.println("SENSOR: ERRO");
  }
  oled.setTextSize(2);
  oled.println(t.status <= CC_STATUS_ALARM ? NOMES[t.status] : "?");
  oled.setTextSize(1);
  oled.printf("TX %s  sig %lums\n", t.tx_ok ? "ok" : "ERRO", (unsigned long)t.sign_ms);
  oled.display();
}

void display_chave(const uint8_t pub[64], uint32_t sign_us_mean) {
  if (!oled_ok) return;
  char hex[17];
  cc_to_hex(pub, 8, hex);
  oled.clearDisplay();
  oled.setCursor(0, 0);
  oled.println("Chave publica (X):");
  oled.println(hex);
  oled.printf("\nassinatura media\n%lu us\n", (unsigned long)sign_us_mean);
  oled.display();
}

void led_update(uint8_t status) {
  bool on = status == CC_STATUS_ALARM || (status == CC_STATUS_WARN && (millis() / 500) % 2);
  digitalWrite(ALARM_LED, on ? HIGH : LOW);
}
