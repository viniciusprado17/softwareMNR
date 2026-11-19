# Integração do protótipo montado (Uno + 2 Heltec) com o software

Registro: 19/11/2026. Base: manual e guia da equipe de 18/11 (cópias em `prototipo_lacor/`).

## 1. O que o protótipo já faz (comprovado pela equipe em 18/11)

SHT31 e GPS ligados ao Arduino Uno. O Uno manda, a cada cerca de 5 s, uma linha de texto
`T:25.18C U:62.69% GPS:SEM FIX` pelo D3 (9600 baud). O sinal passa por um divisor de 3 resistores
de 1 kΩ e chega ao GPIO41 da Heltec transmissora, que repassa o texto por LoRa (915 MHz, SF7,
BW 125 kHz, CR 4/5). A Heltec receptora mostra o texto no OLED.

O que faltava: o texto ia **sem assinatura**, e o notebook não recebia nada. O gateway (verificação,
replay, corrente de hash, tela) não participava.

## 2. O que muda

Só o **programa das duas Heltec**. Nenhum fio muda, o Uno não é regravado.

| Placa | Antes (sketch da equipe) | Depois (firmware do repositório) |
|---|---|---|
| Arduino Uno | `MNR_Uno` | **Igual, não regravar** |
| Heltec transmissora | `MNR_Transmissor`: repassa o texto | `firmware/node`, ambiente `heltec_v3_node_uno`: lê a linha do Uno no GPIO41, decide OK/ALERTA/ALARME, monta o pacote de 88 bytes, **assina com ECDSA P-256** e transmite |
| Heltec receptora | `MNR_Receptor`: mostra o texto | `firmware/receiver`: repassa cada pacote ao notebook pela USB (`RX,<rssi>,<snr>,<hex>`) |
| Notebook | nada | `run_gateway.bat --port COMx --demo-controls`: verifica a assinatura, rejeita adulteração e replay, grava a corrente de hash e mostra a tela |

Os sketches da equipe ficam guardados em `prototipo_lacor/` para voltar ao estado de 18/11 se
for preciso (Plano B).

Fluxo novo:

```text
SHT31 + GPS -> Uno -> (texto, divisor) -> Heltec transmissora: decide, ASSINA, LoRa
            -> Heltec receptora -> USB -> gateway no notebook: VERIFICA -> corrente de hash -> tela
```

## 3. Detalhes do modo `SENSOR_UNO`

- `firmware/lib/coldchain_core/src/cc_uno.cpp` interpreta a linha. Aceita `T:..C U:..%`, com
  `GPS:SEM FIX` ou `LAT:.. LON:..`. `ERRO SHT31`, linha truncada ou valor fora da faixa do SHT31
  (de -40 a 125 °C, de 0 a 100 %) viram leitura inválida. Testes: `bash firmware/test_host/run.sh`.
- Uma leitura só vira pacote se chegou do Uno há menos de 15 s (`UNO_MAX_AGE_MS`). Se o Uno parar,
  o nó para de transmitir e o gateway marca "silêncio". O nó nunca repete uma temperatura velha.
- Ciclo do nó: 10 s (bancada). O Uno manda a cada 5 s, então cada pacote usa a leitura mais recente.
- Com posição do GPS na linha, LAT e LON entram no pacote (`lat_e6`, `lon_e6`). Sem fix, ficam
  marcadas como inválidas, como já previsto em `docs/PACOTE.md`.
- O pacote é o mesmo de 88 bytes (`packet.py`). O formato e a curva não mudaram.
- O OLED das duas Heltec fica girado (`DISPLAY_ROTATION=2`), como nos sketches da equipe.
- Na serial USB da transmissora aparecem `INFO,uno,<linha>` (cada linha recebida do Uno) e
  `TX,<seq>,<hex>` (cada pacote assinado).

## 4. Passo a passo no notebook

Antenas LoRa rosqueadas nas duas Heltec antes de ligar. Uma placa por vez no USB.

1. Atualizar: `git pull`.
2. Gerar a chave do nó 1 (uma vez só):
   `python tools/provision_node.py --node-id 1`
   Isso cria `firmware/include/keys.h` e `keys/private/node_1.pem` (fora do git) e
   `keys/nodes.json` (chave pública que o gateway confia).
3. **Transmissora** no USB (a que tem os fios do divisor). Gravar:
   `python -m platformio run -d firmware/node -e heltec_v3_node_uno -t upload --upload-port COMx`
   Conferir na serial (115200): `INFO,sensor=uno_serial`, `INFO,uno,T:...` a cada 5 s e
   `TX,<seq>,<hex>` a cada 10 s. Em seguida:
   `python tools/check_fw_output.py --port COMx --seconds 30`
   deve aceitar os pacotes com a chave de `keys/nodes.json`.
4. Desligar a transmissora do notebook e alimentar pelo powerbank (o Uno continua como antes).
5. **Receptora** no USB. Gravar:
   `python -m platformio run -d firmware/receiver -t upload --upload-port COMy`
   Conferir na serial: `INFO,receptor fw=receiver-1.0` e linhas `RX,<rssi>,<snr>,<hex>`.
6. Fechar o monitor serial (só um programa por porta) e abrir a tela:
   `run_gateway.bat --port COMy --demo-controls`
   Critério: pacotes **aceitos** com a temperatura real; mão no sensor muda a curva.
7. Testar com dados reais: Adulterar pacote, Reenviar pacote, Adulterar o banco + Verificar corrente.

## 5. O que dizer e o que não dizer

Pode dizer, depois de passar no item 6:
- leitura real do SHT31, assinada com ECDSA P-256 na Heltec, transmitida por LoRa a 915 MHz e
  verificada no gateway, que rejeita adulteração e replay e grava uma corrente de hash.

Precisa declarar:
- A assinatura acontece na Heltec transmissora, não no sensor. O trecho Uno para Heltec é um fio
  com texto sem autenticação. Em produção, o sensor ficaria direto no nó que assina (era o plano do
  firmware `heltec_v3_node`, com o SHT31 no Wire1) ou num elemento seguro.
- LoRa ponto a ponto, não LoRaWAN. Sem GSM e sem nuvem.
- GPS: sentenças válidas recebidas, posição por satélite ainda não validada (manual de 18/11).
- Tempo de assinatura medido no ESP32: ver `docs/MEDICOES.md`. Não comparar com os 0,59 ms do artigo.

## 6. Pontos de atenção do hardware (do manual de 18/11)

- O SHT31 está alimentado com **5 V no Uno**. O manual registra que o módulo testado funcionou
  assim. Isso só é seguro se o módulo tiver regulador de tensão na placa (a maioria dos módulos
  GY-SHT31-D tem). Não mudar a ligação agora; conferir o regulador antes de reaproveitar o sensor
  em outra placa. Ligado direto a uma Heltec, o SHT31 vai sempre em 3,3 V.
- Nunca ligar o D3 do Uno direto no GPIO41: o ESP32-S3 aceita no máximo 3,3 V. O divisor
  (cerca de 2/3 de 5 V, perto de 3,3 V) é obrigatório.
- GND comum entre Uno e transmissora (fio roxo). Sem ele a serial vira lixo.

## 7. Achados da bancada de 19/11

- **Terra comum:** com Uno e transmissora em fontes diferentes, nenhuma linha do Uno chegava. Resolvido
  com um fio direto do GND da Heltec (pela coluna dela na protoboard) ao GND do Uno, além do roxo.
- **Powerbank desliga sozinho** quando a transmissora consome pouco. A Heltec reinicia e o OLED mostra
  `SENSOR: ERRO` de forma intercalada. Na demonstração, alimentar a transmissora pelo notebook ou usar
  um powerbank com modo de baixa corrente. Testar 5 minutos antes de confiar.
- **Só um cabo USB-C de dados** funcionou; o outro só alimenta. A receptora precisa do cabo de dados
  (serial para o gateway). Comprar um cabo de dados reserva antes da viagem.
- **Uno conferido** pela serial (COM do Uno, 115200): linhas válidas a cada 5 s, sem `ERRO SHT31`;
  GPS com sentenças válidas e sem fix em ambiente fechado.
- Com o gateway aberto, nenhum outro programa pode abrir a porta da receptora (dá "Acesso negado").
