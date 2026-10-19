# CLAUDE.md — Projeto MNR 2026 (Cadeia de Frio IoT + ECDSA)

**Documento mestre: `docs/ESPECIFICACAO.md`** (funcao do sistema, escopo, arquitetura, pacote, firmware, gateway, testes, plano de tarefas A1..B8). Em caso de duvida, ele manda. Este arquivo e o resumo.

Contexto completo para desenvolvimento. Leia antes de qualquer tarefa.

## Quem e o que
- Equipe LACOR/UNIT (Aracaju): Vinicius Prado Sobral (presidente da LACOR, lidera o dev), Matheus Felipe Pereira Santos, Julia Lira Santana Rodrigues da Cunha, Manuela Silva Santos Souza, Iasmin Silva de Menezes, Prof. Luiz Gomes da Cunha Neto (orientador).
- Evento: MNR 2026 (RoboCup Brasil), fase nacional em Joao Pessoa, **23 a 29/11/2026**. Categoria Ensino Superior / Pesquisa Tecnologica. Artigo aprovado nos Anais.
- Titulo: "Logistica Segura de Cadeia de Frio para Orgaos e Vacinas: Arquitetura IoT e Ledger Distribuido com Validacao Criptografica Computacional para o Contexto Brasileiro e Nordestino".

## O que o projeto faz
No de borda mede temperatura (e opcionalmente umidade/GPS), decide o estado (OK/ALERTA/ALARME), **assina** a leitura com ECDSA P-256 + SHA-256 e transmite por LoRa. Um gateway verifica a assinatura, rejeita adulteracao e replay, e grava em um ledger com cadeia de hash (SQLite). Dashboard e nuvem sao camadas opcionais.

Fluxo: `Sensor -> No (ESP32) -> LoRa -> Gateway (Heltec por USB + Raspberry Pi) -> Ledger -> Dashboard/Nuvem`.

## Hardware
- 2x Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262 + OLED), faixa 863-928 MHz. **Usar 915 MHz** (Brasil).
- 2x SHT31-D (I2C). O OLED da Heltec usa o I2C padrao: o sensor vai em outros pinos (Wire1). Conferir pinout.
- 1x GPS NEO-6M (UART). **Opcional**: sem sinal em ambiente fechado, nao depender dele.
- Ja no LACOR: protoboard, jumpers, LEDs, resistores, 2x Arduino Uno, 2x Raspberry Pi 3B.
- Antena sempre conectada antes de transmitir.
- Pedido do AliExpress feito em 19/10/2026 e **ja enviado** (confirmado em 19/10 a noite). Janela de entrega informada: **30/10 a 10/11**. Nao precisa mais cancelar nem comprar nacional. Ate as pecas chegarem, desenvolver sem hardware (Python, vetores, firmware que compila). Plano B se o hardware nao funcionar ate 5/11: apresentar simulacao + gateway + video, com tabela "Artigo x demonstracao".

## Decisoes tecnicas
- Curva: **P-256 (secp256r1)** em software e firmware (padrao atual). O artigo usou secp256k1 (biblioteca Python `ecdsa`, seed 42) e planeja micro-ecc, que suporta as duas. **Decidido em 19/10 (issue #9): manter P-256**, declarada como evolucao do prototipo (padrao IoT, compativel com ATECC608 e AWS IoT). Ver `docs/DECISOES.md`.
- Assinatura em formato bruto **r||s (64 bytes)**, nao DER. O pacote total tem 88 bytes (24 payload + 64 assinatura), cabe no limite do LoRa (255).
- Hash SHA-256 sobre o payload. Anti-replay por `seq` monotonico por no.
- Chave privada embutida no firmware so no prototipo. Em producao: elemento seguro.
- Latencia 0,59 ms do artigo foi em Python no PC. **Reconferir no ESP32.**
- "Ledger distribuido" na pratica e uma cadeia de hash replicada. Nao chamar de blockchain.
- Sem concentrador LoRaWAN real nem modulo GSM: LoRa ponto a ponto emulando LoRaWAN.

## Escopo em camadas (cortar de tras para frente)
1. **Obrigatorio:** sensor, decisao, pacote assinado por LoRa, verificacao, rejeicao de adulteracao.
2. Gateway no Pi com ledger SQLite e tela simples.
3. MQTT/AWS IoT Core e GPS.

## Cronograma (hoje: 19/10)
- ate 31/10: firmware lendo sensor + LoRa entre os 2 nos
- ate 7/11: assinatura e verificacao no firmware
- ate 12/11: demonstracao ponta a ponta fechada
- 12 a 22/11: ensaio, banner, video

## Alinhamento com o artigo aprovado (lido em 19/10, 5 paginas)
O artigo e honesto: so tem **simulacao em Python**; todo hardware esta como "Planejado" (Tabela 1) e a conclusao diz que a validacao fisica nao foi executada. Nunca afirmar na demonstracao algo que o artigo nao tenha ou que nao tenha sido medido. Resultados do artigo: 14/14 classificacao (2 a 15 C, limiar 8 C), 50/50 adulteracoes, 0,59 ms (n=100, PC). `python tools/repro_artigo.py` reproduz os 3 testes (a latencia em Python de hoje nao e comparavel; medir no ESP32).
Diferencas a declarar (ver Secoes 1.3 e 13 da especificacao):
- curva secp256k1 (artigo) x P-256 (codigo); ciclo 60 s (artigo) x 10 s (bancada), manter 60 s configuravel;
- payload JSON (artigo) x pacote binario de 88 bytes; bloco encadeado no no (artigo) x corrente no gateway;
- LoRaWAN/GSM/MQTT/AWS/LittleFS (artigo) x LoRa ponto a ponto (camada 3 opcional);
- ESP32-WROOM-32 + SX1276 TTGO (artigo) x Heltec V3 ESP32-S3 + SX1262 (comprada);
- MPU-6050, DS3231, Reed Switch, bateria 5.000 mAh, autonomia 72 h: nao comprados/nao medidos (sem DS3231 o timestamp vem do gateway ou relogio interno);
- frequencia: o artigo nao cita; usar 915 MHz.
A Tabela 3 do artigo (evolucoes propostas) e o roteiro: SHT31 real, latencia real, chaves no ESP32, ataque coordenado, limiares parametrizaveis.

## Estado do codigo (atualizado 19/10)
- Bloco A (A1..A8) feito e testado (56 testes): `python -m unittest discover -s tests`.
- `src/coldchain/`: pacote, cripto P-256, decisao, ledger (colunas extras, tabela `events`, `verify_chain(keys)` -> `ChainCheck(ok, bad_idx, reason)`, migracao, bloco `resync`), gateway (status recalculado -> `status_divergente`, silencio, RSSI/SNR, eventos de rejeicao, `--reset-node`), `serial_bridge.py` (+ `--simulate`), `config.py` (`config.toml`, `keys/nodes.json`), `webapp.py` + `static/` (tela, API da Secao 10.5, `--demo-controls`).
- `firmware/`: PlatformIO para Heltec V3. `lib/coldchain_core` (pacote, SHA-256 proprio, ECDSA micro-ecc deterministico, autoteste) e portavel; `bash firmware/test_host/run.sh` compila no PC e o Python confere as assinaturas. `node/`, `receiver/`, `vectest/` escritos mas **nunca gravados em placa** (sem hardware ainda). O CI compila os tres.
- `tools/`: `provision_node.py` (chaves -> `keys.h`/`nodes.json`), `check_fw_output.py` (confere serial), `bench_python.py` (A8), `airtime.py`, `gen_vectors.py`, `gen_firmware_vectors.py`, `repro_artigo.py`.
- Guia do Bloco B: `docs/GUIA_HARDWARE.md`. Medicoes: `docs/MEDICOES.md`. Diferencas: `docs/ARTIGO_X_DEMONSTRACAO.md`. Decisoes: `docs/DECISOES.md`.
- Tela sem hardware: `./run_gateway.sh --simulate --demo-controls` (http://127.0.0.1:8000).

## Convencoes
- Python 3.10+. Dependencias: `cryptography`, `pyserial`, `fastapi`, `uvicorn` (`requirements.txt`; 3.10 tambem `tomli`). Sem frameworks pesados.
- O formato do pacote e a fonte da verdade em `packet.py`; o firmware deve espelhar byte a byte (big-endian).
- Antes de mudar o formato do pacote, atualizar `docs/PACOTE.md` e os testes.
- Comentarios e docs em portugues, codigo em ingles.
