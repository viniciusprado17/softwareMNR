#include "LoRaWan_APP.h"
#include "Arduino.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Configuracao do radio
#define RF_FREQUENCY 915000000  // 915 MHz
#define LORA_BANDWIDTH 0        // 125 kHz
#define LORA_SPREADING_FACTOR 7
#define LORA_CODINGRATE 1       // 4/5
#define LORA_PREAMBLE_LENGTH 8

// Display integrado da Heltec V3
#define OLED_LARGURA 128
#define OLED_ALTURA 64
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RESET 21
#define OLED_ENDERECO 0x3C
#define VEXT 36

Adafruit_SSD1306 telaOled(
  OLED_LARGURA,
  OLED_ALTURA,
  &Wire,
  OLED_RESET
);

static RadioEvents_t eventosRadio;

bool displayFuncionando = false;
bool iniciarRecepcao = true;
bool atualizarDisplay = false;

char ultimaMensagem[48] = "";
int16_t ultimoRssi = 0;
unsigned long pacotesRecebidos = 0;

void mostrarAguardando() {
  if (!displayFuncionando) return;

  telaOled.clearDisplay();
  telaOled.setTextSize(1);
  telaOled.setTextColor(SSD1306_WHITE);
  telaOled.setCursor(0, 0);

  telaOled.println("MNR - RECEPTOR");
  telaOled.println("---------------------");
  telaOled.println("LoRa: 915 MHz");
  telaOled.println();
  telaOled.println("Aguardando mensagem...");

  telaOled.display();
}

void mostrarPacote() {
  if (!displayFuncionando) return;

  telaOled.clearDisplay();
  telaOled.setTextSize(1);
  telaOled.setTextColor(SSD1306_WHITE);
  telaOled.setCursor(0, 0);

  telaOled.println("MNR - RECEPTOR");
  telaOled.println("---------------------");
  telaOled.println("Recebido:");
  telaOled.println(ultimaMensagem);

  telaOled.print("RSSI: ");
  telaOled.print(ultimoRssi);
  telaOled.println(" dBm");

  telaOled.print("Pacotes: ");
  telaOled.println(pacotesRecebidos);

  telaOled.display();
}

void aoReceber(
  uint8_t *dados,
  uint16_t tamanho,
  int16_t rssi,
  int8_t snr
) {
  Radio.Sleep();

  Serial.print("\nRecebido: ");

  // Mostra o pacote completo na serial
  for (uint16_t i = 0; i < tamanho; i++) {
    Serial.write(dados[i]);
  }

  Serial.print(" | RSSI: ");
  Serial.print(rssi);
  Serial.print(" dBm | SNR: ");
  Serial.print(snr);
  Serial.println(" dB");

  // Copia a mensagem respeitando o tamanho do buffer
  uint16_t tamanhoCopia = tamanho;

  if (tamanhoCopia >= sizeof(ultimaMensagem)) {
    tamanhoCopia = sizeof(ultimaMensagem) - 1;
  }

  memcpy(ultimaMensagem, dados, tamanhoCopia);
  ultimaMensagem[tamanhoCopia] = '\0';

  ultimoRssi = rssi;
  pacotesRecebidos++;

  atualizarDisplay = true;
  iniciarRecepcao = true;
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\nMNR - Receptor LoRa");
  Serial.println("Frequencia: 915 MHz");

  // Inicializa a placa para o radio
  Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);

  // Liga a alimentacao do display
  pinMode(VEXT, OUTPUT);
  digitalWrite(VEXT, LOW);
  delay(100);

  Wire.begin(OLED_SDA, OLED_SCL);

  displayFuncionando = telaOled.begin(
    SSD1306_SWITCHCAPVCC,
    OLED_ENDERECO
  );

  if (displayFuncionando) {
    telaOled.setRotation(2);
    mostrarAguardando();
  } else {
    Serial.println("Falha ao iniciar display OLED.");
    Serial.println("O receptor continuara pela serial.");
  }

  eventosRadio.RxDone = aoReceber;

  Radio.Init(&eventosRadio);
  Radio.SetChannel(RF_FREQUENCY);

  Radio.SetRxConfig(
    MODEM_LORA,
    LORA_BANDWIDTH,
    LORA_SPREADING_FACTOR,
    LORA_CODINGRATE,
    0,
    LORA_PREAMBLE_LENGTH,
    0,
    false,
    0,
    true,
    0,
    0,
    false,
    true
  );

  Serial.println("Receptor pronto.");
}

void loop() {
  if (iniciarRecepcao) {
    iniciarRecepcao = false;
    Radio.Rx(0);
  }

  Radio.IrqProcess();

  if (atualizarDisplay) {
    atualizarDisplay = false;
    mostrarPacote();
  }
}
