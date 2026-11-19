# Manual de montagem manutenção e backlog do protótipo LACOR MNR

**Registro:** 18 de novembro de 2026. Documento de referência para remontar, testar e manter o protótipo. Antes de desmontar, fotografe e identifique os fios; a montagem real e os programas gravados são a referência para futuras conferências.

## 1. O que foi comprovado

O SHT31 mediu temperatura e umidade no Uno. O Uno transmitiu essas leituras pela serial à Heltec transmissora, que as enviou via LoRa para a Heltec receptora; o receptor mostrou as mensagens em seu OLED. O display da transmissora foi atualizado para mostrar LACOR + MNR. Após a montagem na caixa o usuário confirmou o funcionamento.

O GPS enviou sentenças válidas ao Uno, mas no último registro serial disponível ainda mostrava `GPS:SEM FIX`. Isso confirma comunicação com o módulo, não uma posição por satélite. Validar latitude e longitude no receptor em céu aberto. A assinatura ECDSA, o software do notebook, alertas, LoRaWAN, GSM e nuvem não foram comprovados no fluxo completo descrito aqui; não apresentá-los como já integrados.

## 2. Arquitetura

```text
SHT31 ── I2C ──► Uno ◄── serial ── GPS + antena
                     │ D3, 9600 baud
                     ▼
             Divisor de tensão 1k + 1k + 1k
                     │ ponto central → GPIO41
                     ▼
            Heltec transmissora ── LoRa 915 MHz ──► Heltec receptora
                     │ OLED LACOR + MNR                  │ OLED / USB
```

O rádio é LoRa ponto a ponto, não demonstra por si só LoRaWAN. O sinal no monitor “Envio concluído pelo rádio” confirma o término da transmissão, não que o receptor a recebeu. A confirmação de recepção é a mensagem no OLED ou no monitor do receptor.

## 3. Peças e identificação

- Arduino Uno, SHT31, módulo GPS GY-GPS6MV2 com antena, duas Heltec WiFi LoRa 32 V3, duas antenas LoRa para a faixa 863–928 MHz, protoboard, jumpers e três resistores de 1 kΩ.
- Marque fisicamente as Heltecs como **TRANSMISSORA** (conectada ao Uno) e **RECEPTORA** (apresenta leituras). Conecte as antenas LoRa antes de transmitir. Não confunda a antena GPS com as antenas LoRa.
- As cores registradas abaixo são as informadas pelo usuário. Cores não indicam função universal; confirme sempre as inscrições nas placas e o ponto de destino.

## 4. Ligações do SHT31

| Pino do SHT31 | Cor | Destino no Uno |
|---|---|---|
| VIN / VCC | Vermelho | 5V |
| GND | Preto | GND |
| SDA | Laranja | A4 |
| SCL | Amarelo | A5 |

O endereço I2C observado e usado pelo código é 0x44. Essas ligações se referem ao módulo testado, não à tensão permitida por qualquer sensor SHT31 avulso.

## 5. Ligações do GPS

| Pino do GPS | Cor | Destino no Uno |
|---|---|---|
| VCC | Vermelho | 3.3V |
| GND | Azul | GND |
| TX | Verde | D4 |
| RX | Sem fio | Desconectado |

A antena GPS permanece conectada ao módulo, com a face branca voltada para o céu. O GPS transmite a 9600 baud. No programa, D5 é definido como TX do Uno para a serial de software do GPS, mas fica fisicamente desconectado. O módulo enviou sentenças válidas nessa configuração de alimentação; a posição ainda precisa ser validada.

## 6. Divisor de tensão e GND comum

O D3 do Uno opera com sinais de 5 V. A entrada GPIO41 da Heltec recebe o sinal pelo divisor, nunca diretamente do D3. Os três resistores usados são **1 kΩ: marrom, preto, vermelho, dourado**; não têm polaridade. As demais cores disponíveis eram 330 Ω (laranja, laranja, marrom, dourado) e 10 kΩ (marrom, preto, laranja, dourado), e não substituem diretamente os três de 1 kΩ.

```text
Uno D3 ── fio branco ── R1 1k ── ponto X ── R2 1k ── R3 1k ── GND comum
                                    │                               │
                          fio amarelo → Heltec GPIO41               ├─ Uno GND
                                                                    └─ fio roxo → Heltec GND
```

O ponto X é a junção entre R1, R2 e o fio amarelo. O fio roxo liga o GND da Heltec ao mesmo nó elétrico que o GND do Uno e a ponta final de R3. Os GNDs preto do SHT31 e azul do GPS também se conectam ao GND do Uno. Não pressupor que duas fileiras de protoboard, seus lados ou trilhos longos estão ligados: confira a estrutura da sua protoboard.

No teste anterior, o A0 do Uno mediu cerca de 674/1023 no ponto X com a saída em nível alto. O valor é coerente com aproximadamente dois terços da referência do conversor, mas não é medição calibrada de tensão.

### Exemplo de distribuição em protoboard

Os números são um exemplo para remontagem, não uma confirmação da posição física atual. Dentro de cada linha use o mesmo grupo conectado de cinco furos no mesmo lado do canal central. Cada resistor deve unir grupos diferentes.

| Grupo de furos | Ligações |
|---|---|
| Linha 10 | Branco vindo do D3 e primeira ponta de R1 |
| Linha 15 | Segunda ponta de R1, primeira ponta de R2 e amarelo para GPIO41 |
| Linha 20 | Segunda ponta de R2 e primeira ponta de R3 |
| Linha 25 | Segunda ponta de R3, fio para GND do Uno e roxo para GND da Heltec |

## 7. Heltecs e parâmetros

| Item | Transmissora | Receptora |
|---|---|---|
| Ligação externa de dados | GPIO41 recebe a saída do divisor | Nenhuma; recebe pelo rádio |
| GND externo | Comum com o Uno | Não precisa de ligação por fio ao transmissor |
| Antena | Antena LoRa conectada | Antena LoRa conectada |
| USB | Alimentação e monitor serial | Alimentação e monitor serial/notebook |
| OLED | Mensagem LACOR + MNR | Mensagem recebida e informações do rádio |

Ambas usam 915 MHz, largura 125 kHz (índice 0), SF7, codificação 4/5 (índice 1), preâmbulo 8, CRC ligado e IQ normal, conforme os códigos recuperados. A potência configurada na transmissora é 14 dBm. UART Uno–Heltec: 9600 baud; monitores USB: 115200 baud. OLED integrado: SDA GPIO17, SCL GPIO18, reset GPIO21, alimentação VEXT GPIO36 ativo em LOW, endereço 0x3C. Esses pinos são internos ao display e não requerem fios externos nesta montagem.

COM4 para Uno e COM5 para Heltec apareceram nos testes, mas as portas COM podem mudar; confirme em Ferramentas > Porta antes de carregar cada código.

## 8. Remontagem passo a passo

1. Desligue USB e powerbank. Identifique Uno, GPS, SHT31, transmissora e receptora. Consulte fotos da montagem anterior.
2. Inspecione soldas e encaixes, sem puxar fios pelo cabo. Fixe a protoboard e as placas sem pressionar trilhas, componentes ou conectores.
3. Conecte o SHT31 ao Uno conforme a seção 4.
4. Conecte GPS e antena conforme a seção 5; deixe o RX do GPS sem fio.
5. Monte o divisor com três resistores de 1 kΩ e conecte branco D3, amarelo GPIO41 e roxo GND conforme a seção 6.
6. Conecte o GND do Uno ao GND comum da protoboard; confirme que o GND da Heltec, SHT31 e GPS também chegam ao mesmo GND.
7. Conecte as antenas LoRa. Identifique o USB de cada placa e mantenha as ligações organizadas para não tracionar soldas nem o conector de antena.
8. Confira os pontos de alimentação: SHT31 VIN para 5V e GPS VCC para 3.3V. Confira o fio amarelo da Heltec no ponto X, não em D3 ou 5V.
9. Alimente as placas, confira os displays e abra o monitor serial quando necessário. Confira que os dados do Uno chegam ao receptor.
10. Em céu aberto, aguarde o GPS obter posição e confirme LAT e LON; anote a duração e registre o resultado.

## 9. Arduino IDE e restauração dos programas

Há três sketches independentes. Use os arquivos anexos em pastas com o mesmo nome do .ino ou copie o programa integral da seção 13. Salve uma cópia dos sketches em local seguro. Não é necessário regravar placas que já funcionam.

| Sketch | Placa no IDE | Bibliotecas |
|---|---|---|
| MNR_Uno | Arduino Uno | Wire, SoftwareSerial, Adafruit SHT31, TinyGPSPlus e dependências da SHT31 |
| MNR_Transmissor | Heltec WiFi LoRa 32(V3) | Heltec ESP32 Dev-Boards, Wire, Adafruit GFX, Adafruit SSD1306 e dependências |
| MNR_Receptor | Heltec WiFi LoRa 32(V3) | Heltec ESP32 Dev-Boards, Wire, Adafruit GFX, Adafruit SSD1306 e dependências |

Passos para restaurar: abra o sketch correto, selecione sua placa e porta, compile, confirme a placa selecionada e carregue. Ligue a antena antes de transmitir. Ao trocar de janela, confira novamente placa e porta: tentar compilar SoftwareSerial do Uno para Heltec pode causar erro. O código do receptor foi recuperado da resposta corrigida após o conflito de nome `display`; Uno e transmissora foram recuperados do cache de compilação. A recuperação não lê a memória atual das placas e não comprova que elas não foram alteradas posteriormente.

## 10. Operação e testes

- No monitor do Uno, a cada cerca de 5 segundos: `T:...C U:...% GPS:SEM FIX`, ou LAT e LON quando há posição válida e recente. Taxa do monitor: 115200.
- `Caracteres recebidos do GPS` e `Sentencas validas` crescentes indicam recepção de mensagens válidas; não garantem posição. `GPS:SEM FIX` significa que o programa não dispõe de posição válida e recente.
- Na transmissora: `Recebido do Uno`, `Enviando por LoRa` e `Envio concluido pelo radio`. O OLED mostra a identificação fixa.
- No receptor: pacote no OLED ou no monitor serial. O código recuperado reserva 48 bytes para o texto no OLED, portanto pode truncar mensagens longas. Compare a linha completa pela serial antes de concluir que todas as coordenadas são exibidas.
- Faça teste de duração e registre horário, número de falhas e condições; a recepção de alguns pacotes não estabelece alcance, autonomia ou confiabilidade estatística.

## 11. Manutenção e diagnóstico

Desligue antes de reposicionar fios ou trabalhar em soldas. Evite umidade ou condensação nos circuitos; não submerja o módulo do sensor nem presuma que ele seja impermeável. Fixe os cabos sem esmagá-los e mantenha acesso aos botões, USB e antenas.

| Sintoma | Verificação inicial |
|---|---|
| SHT31 não encontrado ou erro de leitura | Conferir VIN 5V, GND, SDA A4, SCL A5, encaixes e soldas; conferir endereço 0x44. |
| Uno lê, transmissora não recebe | Conferir D3 branco, os três resistores, ponto X, GPIO41 amarelo e GND comum roxo; serial entre placas em 9600. |
| Linha vazia, lixo ou descartada | Verificar encaixes e GND, reiniciar após conferir conexões e observar se se repete; não concluir que é apenas software. |
| Caracteres GPS zero | Verificar alimentação, GND, TX verde em D4, encaixes e baud 9600. |
| Caracteres GPS sobem, sentenças válidas não | Conferir conexão e baud; verificar interferência ou perdas e registrar o log. |
| Sentenças válidas, GPS sem fix | Antena branca para cima em céu aberto e tempo para adquirir posição; não usar coordenada antiga como posição atual. |
| Transmissora envia, receptor não mostra | Verificar antenas, alimentação, placa receptora correta, parâmetros iguais e monitor serial do receptor. |
| Display apagado | Conferir alimentação e placa selecionada; monitor a 115200; o programa pode continuar sem display. |
| `multiple definition of display` | A biblioteca Heltec já usa esse nome; manter os identificadores telaOled ou oledTransmissor dos códigos incluídos. |

## 12. Backlog de desenvolvimento e apresentação

| Prioridade | Atividade | Critério de conclusão | Situação |
|---|---|---|---|
| Alta | Fix do GPS e percurso completo | LAT/LON atuais no Uno e recebidas na serial do receptor; confirmar visualização no OLED | Pendente no último registro |
| Alta | Estabilidade após montagem | Registrar duração, falhas, reinícios e fotos; confirmar que as conexões permanecem firmes | Usuário confirmou funcionamento; teste prolongado pendente |
| Alta | Cópia de segurança | Guardar sketches, este documento e fotos das ligações | Produzido neste pacote; guardar cópia externa |
| Alta | Proteção e operação da caixa | Fixação, acesso a energia e antenas, proteção contra umidade testados | Conferir na montagem final |
| Média | ECDSA e verificação | Assinar mensagem real e verificar no destino; testar adulteração e registrar versão/chaves de teste sem expor chave privada | Não comprovado no fluxo atual |
| Média | Alerta térmico | Definir limites do caso de uso e verificar alertas com leituras reais, incluindo falha do sensor | Pendente |
| Média | Visualização no notebook | Receber, interpretar e mostrar os pacotes via USB; testar reconexão | Pendente |
| Média | Alcance, autonomia e perda | Medir em condições registradas, com dados e critérios de aceitação | Pendente |
| Baixa | GPS e serial sob carga | Avaliar perdas causadas por duas SoftwareSerial e carga de transmissão; melhorar arquitetura se necessário | Pendente |
| Planejado | LoRaWAN, GSM e nuvem | Integrar e validar com infraestrutura e protocolo apropriados | Arquitetura futura; não comprovada |

## 13. Códigos completos recuperados

Cada bloco corresponde a uma placa. Os mesmos conteúdos estão em arquivos `.ino` separados nas pastas deste pacote. Códigos são cópias recuperadas, sem alteração da placa física; compile apenas se precisar restaurar.

### 13.1 Arduino Uno

```cpp
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
```

### 13.2 Heltec transmissora

```cpp
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
```

### 13.3 Heltec receptora

```cpp
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
```
