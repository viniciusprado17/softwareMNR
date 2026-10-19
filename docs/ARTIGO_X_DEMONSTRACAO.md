# Artigo × demonstração (Seção 13) — atualizar toda semana

Regra: tudo que a demonstração mostrar precisa estar no artigo **ou** declarado aqui como diferença. Quando houver dúvida, declare.

Última atualização: 19/10/2026 (software pronto em simulação; hardware aguardando entrega).

| Item do artigo | Estado na demonstração | Como declarar |
|---|---|---|
| ESP32-WROOM-32 + SX1276 (TTGO), Tabela 1 "Planejado" | Heltec V3 (ESP32-S3 + SX1262). Firmware escrito, **não gravado ainda** | "Trocamos a placa por disponibilidade e custo" |
| SHT31-D | Driver pronto (`firmware/node/src/sensor.cpp`), não testado | "Sensor real, medido" (só depois do T2/T3) |
| ECDSA com SHA-256 | Curva **P-256** no firmware e no gateway | "A simulação usou secp256k1, o protótipo usa P-256, ambas de 256 bits" |
| micro-ecc | **micro-ecc** (`uECC_sign_deterministic`) + SHA-256 próprio | Coincide com o artigo. Nonce determinístico, sem depender do RNG |
| Resultados 14/14, 50/50, 0,59 ms | Reproduzidos com `tools/repro_artigo.py`; latência no ESP32 a medir | "0,59 ms foi em PC. No ESP32 mediu-se X ms" |
| Ciclo de 60 s | Configurável (`SAMPLE_INTERVAL_MS`); bancada em 10 s | Declarar o intervalo usado |
| Payload JSON | Pacote binário de 88 bytes | "Binário por caber no LoRa e reduzir o tempo no ar (154 ms em SF7)" |
| Bloco encadeado no nó | Corrente no gateway (SQLite), com assinatura reconferida em cada bloco | "A corrente é verificada no gateway" |
| LoRaWAN, GSM/4G, MQTT | LoRa ponto a ponto 915 MHz | "Emulamos o enlace. LoRaWAN e GSM são trabalho futuro" |
| Store-and-forward em LittleFS | Não implementado | Trabalho futuro |
| MPU-6050, DS3231, Reed Switch, bateria 5.000 mAh | Não comprados | "Especificados no artigo, fora do protótipo desta fase". Sem DS3231, `ts = 0` e vale a hora do gateway (`rx_ts`) |
| GPS NEO-6M | Firmware pronto (`env:heltec_v3_node_gps`), opcional | "Funciona com céu aberto" ou "trabalho futuro" |
| Autonomia > 72 h | Não medida | "Especificação, não medição" |
| AWS IoT Core | Não implementado | Trabalho futuro |
| Câmara fria | Não testado | "Teste de bancada com caixa térmica e gelo, não é câmara fria validada" |
| Rota Fortaleza → Juazeiro do Norte | Não realizada | "Cenário alvo, não testado em campo" |

## Tabela 3 do artigo × demonstração

| Evolução proposta no artigo | O que a demonstração entrega hoje |
|---|---|
| SHT31-D físico com ruído real | Pendente (hardware) |
| Latência real de transmissão | Pendente; teórico calculado (`tools/airtime.py`) |
| Chaves e assinatura no ESP32 | Firmware pronto e testado no PC contra o Python; pendente na placa |
| Cenário de ataque coordenado | Parcial: adulteração, replay, nó desconhecido e edição do banco (demonstráveis na tela) |
| Motor de validação em nuvem | Não (Camada 3) |
| Limiar por categoria de insumo | Sim: limiares em `config.toml`; o gateway recalcula o status e anota divergência |
| Modelar consumo de bateria | Não |
