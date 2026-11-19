#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "LoRaWan_APP.h"

// Ligacao com o Arduino Uno:
// D3 do Uno -> divisor de tensao -> GPIO41 da Heltec.
// Os GNDs do Uno e da Heltec devem estar conectados.
#define UNO_RX_HELTEC 41

// Display OLED integrado da Heltec V3.
#define OLED_LARGURA 128
#define OLED_ALTURA 64
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RESET 21
#define OLED_ENDERECO 0x3C
#define VEXT 36

// Configuracao do radio LoRa.
#define FREQUENCIA_LORA 915000000
#define POTENCIA_LORA 14
#define LORA_BANDWIDTH 0
#define LORA_SPREADING_FACTOR 7
#define LORA_CODING_RATE 1
#define LORA_PREAMBLE_LENGTH 8

HardwareSerial serialUno(1);

// O nome oledTransmissor evita conflito com a variavel "display"
// que ja existe na biblioteca da Heltec.
Adafruit_SSD1306 oledTransmissor(
  OLED_LARGURA,
  OLED_ALTURA,
  &Wire,
  OLED_RESET
);

static RadioEvents_t eventosRadio;

// Espaco para uma linha enviada pelo Uno.
char linha[100];
size_t posicao = 0;

bool descartandoLinha = false;
bool radioOcupado = false;
bool displayFuncionando = false;

// Mostra a identificacao no display do transmissor.
void mostrarTelaInicial() {
  if (!displayFuncionando) {
    return;
  }

  oledTransmissor.clearDisplay();
  oledTransmissor.setTextColor(SSD1306_WHITE);

  oledTransmissor.setTextSize(2);
  oledTransmissor.setCursor(0, 0);
  oledTransmissor.println("LACOR +");
  oledTransmissor.println("MNR");

  oledTransmissor.setTextSize(1);
  oledTransmissor.setCursor(0, 38);
  oledTransmissor.println("PROJETO");
  oledTransmissor.println("TRANSMISSOR LoRa");
  oledTransmissor.println("915 MHz");

  oledTransmissor.display();
}

// O radio terminou de transmitir.
void aoConcluirEnvio() {
  Serial.println("Envio concluido pelo radio.");
  radioOcupado = false;
}

// O radio nao concluiu a transmissao dentro do prazo.
void aoExpirarEnvio() {
  Radio.Sleep();
  Serial.println("Erro: tempo de envio LoRa esgotado.");
  radioOcupado = false;
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println();
  Serial.println("LACOR + MNR - Transmissor");
  Serial.println("Recebendo do Uno no GPIO41...");
  Serial.println("Frequencia LoRa: 915 MHz");

  // Recebe do Uno a 9600 baud.
  // Neste teste, a Heltec nao envia dados de volta ao Uno.
  serialUno.begin(9600, SERIAL_8N1, UNO_RX_HELTEC, -1);

  // Inicializa a placa e o radio integrado.
  Mcu.begin(HELTEC_BOARD, SLOW_CLK_TPYE);

  // Liga a alimentacao do display integrado.
  pinMode(VEXT, OUTPUT);
  digitalWrite(VEXT, LOW);
  delay(100);

  // Inicializa o barramento I2C do display.
  Wire.begin(OLED_SDA, OLED_SCL);

  displayFuncionando = oledTransmissor.begin(
    SSD1306_SWITCHCAPVCC,
    OLED_ENDERECO
  );

  if (displayFuncionando) {
    // Mantem a mesma orientacao usada no teste anterior do display.
    oledTransmissor.setRotation(2);
    mostrarTelaInicial();
    Serial.println("Display iniciado.");
  } else {
    Serial.println("Falha ao iniciar o display.");
    Serial.println("A transmissao continuara pela serial e pelo LoRa.");
  }

  eventosRadio.TxDone = aoConcluirEnvio;
  eventosRadio.TxTimeout = aoExpirarEnvio;

  Radio.Init(&eventosRadio);
  Radio.SetChannel(FREQUENCIA_LORA);

  Radio.SetTxConfig(
    MODEM_LORA,
    POTENCIA_LORA,
    0,
    LORA_BANDWIDTH,
    LORA_SPREADING_FACTOR,
    LORA_CODING_RATE,
    LORA_PREAMBLE_LENGTH,
    false,
    true,
    0,
    0,
    false,
    3000
  );

  Serial.println("Transmissor pronto.");
}

void loop() {
  // Processa os eventos do radio.
  Radio.IrqProcess();

  while (serialUno.available() > 0) {
    char caractere = (char)serialUno.read();

    // Ignora o retorno de carro; a linha termina em '\n'.
    if (caractere == '\r') {
      continue;
    }

    if (caractere == '\n') {
      if (descartandoLinha) {
        Serial.println("Linha muito longa; descartada.");
      } else if (posicao > 0) {
        linha[posicao] = '\0';

        Serial.print("Recebido do Uno: ");
        Serial.println(linha);

        if (!radioOcupado) {
          Serial.print("Enviando por LoRa: ");
          Serial.println(linha);

          radioOcupado = true;
          Radio.Send((uint8_t *)linha, posicao);
        } else {
          Serial.println("Radio ocupado; leitura nao enviada.");
        }
      }

      posicao = 0;
      descartandoLinha = false;
    } else if (!descartandoLinha) {
      if (posicao < sizeof(linha) - 1) {
        linha[posicao] = caractere;
        posicao++;
      } else {
        // Descarta o restante da linha ate chegar ao fim.
        descartandoLinha = true;
      }
    }
  }

  delay(1);
}
