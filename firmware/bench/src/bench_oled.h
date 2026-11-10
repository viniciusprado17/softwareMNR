// OLED da Heltec V3 para os testes de bancada (mesma inicializacao de firmware/node/src/display.cpp).
#pragma once

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino.h>
#include <Wire.h>

#include "pins.h"

static Adafruit_SSD1306 oled(128, 64, &Wire, OLED_RST);
static bool oled_ok = false;

static bool oled_begin() {
  pinMode(VEXT_CTRL, OUTPUT);
  digitalWrite(VEXT_CTRL, LOW);  // liga Vext (alimenta o OLED)
  delay(50);
  Wire.begin(OLED_SDA, OLED_SCL);
  oled_ok = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  if (oled_ok) {
    oled.setTextColor(SSD1306_WHITE);
    oled.setTextSize(1);
    oled.clearDisplay();
    oled.display();
  }
  return oled_ok;
}

// Ate 4 linhas; a primeira em tamanho grande.
static void oled_show(const char* big, const char* l2 = "", const char* l3 = "", const char* l4 = "") {
  if (!oled_ok) return;
  oled.clearDisplay();
  oled.setCursor(0, 0);
  oled.setTextSize(2);
  oled.println(big);
  oled.setTextSize(1);
  oled.println(l2);
  oled.println(l3);
  oled.println(l4);
  oled.display();
}
