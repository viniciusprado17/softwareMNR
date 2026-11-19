#include <Arduino.h>
#include <Wire.h>
#include <SoftwareSerial.h>
#include <Adafruit_SHT31.h>
#include <TinyGPSPlus.h>

// Comunicacao com a Heltec:
// D3 do Uno -> divisor de tensao -> GPIO41 da Heltec.
// D2 e definido como RX, mas fica desconectado.
SoftwareSerial serialHeltec(2, 3);

// Comunicacao com o GPS:
// TX do GPS -> D4 do Uno.
// D5 e definido como TX, mas fica desconectado.
SoftwareSerial serialGPS(4, 5);

Adafruit_SHT31 sensor = Adafruit_SHT31();
TinyGPSPlus gps;

const byte ENDERECO_SENSOR = 0x44;
const unsigned long INTERVALO_ENVIO = 5000;
const unsigned long IDADE_MAXIMA_GPS = 15000;

unsigned long ultimoEnvio = 0;
bool sensorIniciado = false;

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // A Heltec recebe a 9600 baud.
  serialHeltec.begin(9600);

  // O GPS normalmente envia a 9600 baud.
  serialGPS.begin(9600);

  // Mantem a recepcao do SoftwareSerial dedicada ao GPS.
  serialGPS.listen();

  Serial.println();
  Serial.println(F("MNR - SHT31 e GPS"));
  Serial.println(F("GPS TX -> D4 do Uno"));
  Serial.println(F("Enviando para a Heltec pelo D3"));
  Serial.println(F("Aguardando dados..."));
}

void loop() {
  // Processa continuamente os caracteres recebidos do GPS.
  while (serialGPS.available() > 0) {
    gps.encode(serialGPS.read());
  }

  // Envia uma leitura a cada 5 segundos.
  if (millis() - ultimoEnvio < INTERVALO_ENVIO) {
    return;
  }

  ultimoEnvio = millis();

  // Tenta iniciar o sensor se ainda nao estiver pronto.
  if (!sensorIniciado) {
    sensorIniciado = sensor.begin(ENDERECO_SENSOR);

    if (sensorIniciado) {
      Serial.println(F("SHT31 iniciado."));
    }
  }

  float temperatura = 0;
  float umidade = 0;
  bool leituraValida = false;

  if (sensorIniciado) {
    leituraValida = sensor.readBoth(&temperatura, &umidade);

    if (!leituraValida) {
      sensorIniciado = false;
    }
  }

  // Verifica se existe uma posicao valida e recente.
  bool gpsValido = gps.location.isValid() &&
                   gps.location.age() < IDADE_MAXIMA_GPS;

  // Monta a mesma mensagem no monitor serial e para a Heltec.
  if (leituraValida) {
    Serial.print(F("T:"));
    Serial.print(temperatura, 2);
    Serial.print(F("C U:"));
    Serial.print(umidade, 2);
    Serial.print(F("%"));

    serialHeltec.print(F("T:"));
    serialHeltec.print(temperatura, 2);
    serialHeltec.print(F("C U:"));
    serialHeltec.print(umidade, 2);
    serialHeltec.print(F("%"));
  } else {
    Serial.print(F("ERRO SHT31"));
    serialHeltec.print(F("ERRO SHT31"));
  }

  if (gpsValido) {
    Serial.print(F(" LAT:"));
    Serial.print(gps.location.lat(), 6);
    Serial.print(F(" LON:"));
    Serial.print(gps.location.lng(), 6);

    serialHeltec.print(F(" LAT:"));
    serialHeltec.print(gps.location.lat(), 6);
    serialHeltec.print(F(" LON:"));
    serialHeltec.print(gps.location.lng(), 6);
  } else {
    Serial.print(F(" GPS:SEM FIX"));
    serialHeltec.print(F(" GPS:SEM FIX"));
  }

  Serial.println();
  serialHeltec.println();

  // Diagnostico local: nao e enviado por LoRa.
  Serial.print(F("Caracteres recebidos do GPS: "));
  Serial.print(gps.charsProcessed());
  Serial.print(F(" | Sentencas validas: "));
  Serial.println(gps.passedChecksum());
}
