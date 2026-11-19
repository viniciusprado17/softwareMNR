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
- `src/coldchain/`: pacote, cripto P-256, decisao, ledger (colunas extras, tabela `events`, `verify_chain(keys)` -> `ChainCheck(ok, bad_idx, reason)`, migracao, bloco `resync`), gateway (status recalculado -> `status_divergente`, silencio, RSSI/SNR, eventos de rejeicao, `--reset-node`), `serial_bridge.py` (+ `--simulate`), `config.py` (`config.toml`, `keys/nodes.json`), `webapp.py` + `static/` (tela, API da Secao 10.5, `--demo-controls`). A tela tem medidor, trilha animada do pacote (sensor -> no -> LoRa -> gateway -> registro), QR code para abrir no celular (`/api/access`, `vendor/qrcode.js`) e instalavel como app (`manifest.webmanifest`, `sw.js`, so a casca). Tem tambem: verificador independente no navegador (`/verificador`, `verifier-core.js`, paridade JS x Python em `tests/js`), `GET /api/export/chain`, bateria do artigo ao vivo (`POST /api/demo/battery`, gateway descartavel), prova do hash na corrente quebrada (`Ledger.explain_failure`) e MKT/excursoes no grafico (`static/metrics.js`). Testes JS: `node --test tests/js/*.test.mjs`. A simulacao 3D da montagem (https://proto3d-site.vercel.app) e so um link/QR, nao faz parte do gateway.
- `firmware/`: PlatformIO para Heltec V3. `lib/coldchain_core` (pacote, SHA-256 proprio, ECDSA micro-ecc deterministico, autoteste) e portavel; `bash firmware/test_host/run.sh` compila no PC e o Python confere as assinaturas. `node/`, `receiver/`, `vectest/` escritos mas **nunca gravados em placa** (sem hardware ainda). `bench/` = kit de bancada (lifetest, i2cscan, sensor, ping_tx, ping_rx; roteiro no GUIA_HARDWARE). O CI compila os quatro.
- `tools/`: `provision_node.py` (chaves -> `keys.h`/`nodes.json`), `check_fw_output.py` (confere serial), `bench_python.py` (A8), `airtime.py`, `gen_vectors.py`, `gen_firmware_vectors.py`, `repro_artigo.py`.
- Guia do Bloco B: `docs/GUIA_HARDWARE.md`. Medicoes: `docs/MEDICOES.md`. Diferencas: `docs/ARTIGO_X_DEMONSTRACAO.md`. Decisoes: `docs/DECISOES.md`.
- Tela sem hardware: `./run_gateway.sh --simulate --demo-controls` (http://127.0.0.1:8000).

## Notebook da fase nacional (16/11)
- Preparado com `tools/setup_notebook.ps1` em `C:\Users\vinic\Projetos\softwareMNR` (ramo main). 69 testes OK, `vectest` compila.
- Conferido na tela simulada: excursao OK -> ALERTA -> ALARME, adulteracao de pacote (assinatura invalida), replay e adulteracao do banco (corrente quebrada no bloco editado).
- Corrigido: no simulado agora continua o seq do ledger ao reabrir o gateway (antes virava REPLAY em massa).
- `firmware/include/pins.h` **conferido** contra a documentacao oficial da Heltec V3 (pins_arduino.h e GPIO Usage Guide, wiki.heltec.org): OLED SDA/SCL/RST (17/18/21), Vext (36, nivel baixo liga) e pinos do SX1262 batem. GPIO 41/42 livres para o sensor (tem funcao JTAG padrao desativavel, e sao o Wire padrao do framework Arduino; o firmware ja chama `Wire1.begin(41, 42)` explicitamente em `firmware/bench/src/i2cscan.cpp`, sem ambiguidade). Sem bloqueio para ligar o SHT31-D.
- **E1 feito (16/11):** `vectest` gravado nas duas Heltec V3 (COM3, USB-C de dados). As duas imprimem `INFO,vectest fw=vectest-1.0` e `SELFTEST,OK`.
- **E2 feito (16/11):** `check_fw_output.py --vectors` confirma `falhas=0` contra os vetores dourados. Medido na placa 2 (sem sensor/GPS ligados, 240 MHz): assinatura 88,05 ms e verificacao 95,53 ms (n=100, micro-ecc), registrado em `docs/MEDICOES.md` e `docs/ARTIGO_X_DEMONSTRACAO.md`.
- **E3 travado (16/11):** SHT31-D ligado no protoboard (VIN laranja -> 3V3, GND marrom -> GND, SCL amarelo -> GPIO5, SDA vermelho -> GPIO4; nao e Wire1 41/42 do pins.h, mudou para 4/5 na montagem fisica). `firmware/bench/i2cscan` gravado, escaneado em 41/42 (padrao), 42/41 (trocado) e 4/5 (real): sempre `I2C,none`. Repetido ligando os fios direto no sensor, sem protoboard: continua `I2C,none`. Cores conferidas e batendo nos dois lados (sem fio trocado). Descartado ate aqui: pino errado no comando de scan, fio cruzado, protoboard.
- Proximo passo ao retomar: trocar pelo segundo SHT31-D (reserva) ligando os mesmos 4 fios, para isolar se o problema e o sensor ou outra coisa; se sobrar duvida, testar continuidade com multimetro (3V3->VIN, GND->GND, GPIO4->SDA, GPIO5->SCL). Se o sensor continuar nao respondendo, considerar: solda fria nos 4 pontos da Heltec, ou decidir religar no Wire1 oficial (GPIO 41/42) em vez de 4/5 para ficar de acordo com `docs/ESPECIFICACAO.md` e `pins.h`.

## Prototipo montado pela equipe (18/11) e integracao (19/11)
- Montagem real: SHT31 e GPS no Arduino Uno; Uno manda texto `T:..C U:..% GPS:..` a 9600 pelo D3 -> divisor 3x1k -> GPIO41 da Heltec transmissora; LoRa 915 MHz -> Heltec receptora. Manual, guia e sketches originais em `prototipo_lacor/`.
- Integracao: firmware `node` ganhou o ambiente `heltec_v3_node_uno` (`-DSENSOR_UNO=1`): le a linha do Uno (`cc_uno.cpp`, testado em `firmware/test_host`), decide, assina e transmite o pacote de 88 bytes. Receptora usa `firmware/receiver`. Nenhum fio muda; o Uno nao e regravado. Passo a passo: `docs/PROTOTIPO_UNO.md`.
- Nao compilado aqui (PlatformIO bloqueado na sessao da nuvem): compilar no notebook ou CI antes de gravar.
- Declarar: assinatura na Heltec, trecho Uno -> Heltec sem autenticacao; SHT31 em 5 V no Uno (modulo com regulador).

## Maximizacao com o Fable (gatilho do usuario)
Quando o usuario disser **COMECAR MAXIMIZACAO** (com ou sem acento, qualquer caixa): rodar `bash tools/fable_preflight.sh`, e se estiver OK delegar a tarefa inteira de `docs/FABLE_TAREFA.md` a um agente `model: "fable"` (um so, na branch atual, sem worktree), seguindo o "Procedimento do Claude principal" do proprio arquivo (disparo e revisao). Sem a frase, **nao** disparar o Fable: ele consome muito. O firmware nao compila na maquina da sessao (registro do PlatformIO bloqueado): a prova e o CI.

## Convencoes
- Python 3.10+. Dependencias: `cryptography`, `pyserial`, `fastapi`, `uvicorn` (`requirements.txt`; 3.10 tambem `tomli`). Sem frameworks pesados.
- O formato do pacote e a fonte da verdade em `packet.py`; o firmware deve espelhar byte a byte (big-endian).
- Antes de mudar o formato do pacote, atualizar `docs/PACOTE.md` e os testes.
- Comentarios e docs em portugues, codigo em ingles.
