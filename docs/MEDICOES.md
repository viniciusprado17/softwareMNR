# Medições para o artigo (Seção 12.4)

Registrar **data, versão do firmware e condições** de cada medição. Nunca preencher sem medir; o que não foi feito fica "não medido".

## 1. Tempo de assinatura e verificação

| Data | Onde | Firmware / versão | Operação | n | Média | Mín | Máx | Desvio | Obs. |
|---|---|---|---|---|---|---|---|---|---|
| 19/10/2026 | PC de desenvolvimento (x86_64, Python 3.13, OpenSSL) | `tools/bench_python.py` | assinatura | 200 | 0,028 ms | 0,025 | 0,051 | 0,004 | **Não comparável** com o artigo nem com o ESP32 |
| 19/10/2026 | idem | idem | verificação | 200 | 0,078 ms | 0,071 | 0,122 | 0,009 | idem |
| | ESP32-S3 (Heltec V3) | vectest-1.0 (`INFO,bench_sign_us`) | assinatura | 100 | não medido | | | | |
| | ESP32-S3 (Heltec V3) | vectest-1.0 (`INFO,bench_verify_us`) | verificação | 100 | não medido | | | | |
| | Raspberry Pi 3B | `tools/bench_python.py` | verificação | 1000 | não medido | | | | |

Referência do artigo: 0,59 ms (mín 0,51, máx 0,69), n = 100, biblioteca Python `ecdsa` (secp256k1) em CPU de PC.

## 2. Tempo no ar (88 bytes, BW 125 kHz, CR 4/5, preâmbulo 8, CRC)

| SF | Teórico (`tools/airtime.py`) | Medido no nó (`tx_us`) |
|---|---|---|
| 7 | 153,9 ms | não medido |
| 9 | 492,5 ms | não medido |

## 3. Enlace (taxa de entrega, RSSI, SNR)

| Data | Cenário | SF | Enviados (seq) | Aceitos | Entrega | RSSI médio | SNR médio |
|---|---|---|---|---|---|---|---|
| | 1 m, linha de visada | 7 | | | | | |
| | 5 m | 7 | | | | | |
| | Através de parede | 7 | | | | | |

## 4. Detecção de adulteração com hardware

| Data | Tentativas | Detectadas | Método |
|---|---|---|---|
| | 50 | | botão "Adulterar pacote" sobre pacotes reais |

## 5. Ensaio de 30 minutos (T12)

| Data | Duração | Pacotes enviados | Aceitos | Eventos de silêncio | Travou? |
|---|---|---|---|---|---|

## 6. Consumo (opcional, Seção 11.4)

| Modo | Corrente média | Instrumento |
|---|---|---|
| Ativo transmitindo | não medido | |
| Entre amostras | não medido | |
