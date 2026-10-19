# Cadeia de Frio Segura — MNR 2026 (LACOR/UNIT)

Sistema que **prova que a temperatura registrada no transporte de vacinas e órgãos não foi alterada depois de medida**.

```
[SHT31-D] -I2C-> [Heltec V3 NÓ] ~~LoRa 915 MHz, 88 bytes~~> [Heltec V3 RECEPTOR] -USB-> [Raspberry Pi]
                  mede, classifica,                           repassa RX,<rssi>,<snr>,<hex>   ponte serial
                  assina ECDSA P-256                                                          gateway (verifica)
                  OLED + LED                                                                  ledger SQLite (hash)
                                                                                              tela web local
```

- **Nó sensor:** mede, classifica (OK / ALERTA / ALARME, faixa 2–8 °C), monta um pacote binário de 88 bytes e o **assina** (ECDSA P-256 sobre SHA-256).
- **Gateway:** confere tamanho, versão, nó, **assinatura** e **replay**; grava o que é válido num **registro encadeado por hash**. Rejeições viram eventos, fora da corrente.
- **Tela:** leituras, gráfico, eventos, verificação da corrente e botões de ataque para a demonstração.

Projeto da LACOR (Universidade Tiradentes, Aracaju) para a **Mostra Nacional de Robótica 2026**, fase nacional em João Pessoa, 23 a 29/11/2026.
Documento mestre: [`docs/ESPECIFICACAO.md`](docs/ESPECIFICACAO.md) (também em [PDF](docs/Especificacao_Software_MNR2026.pdf)). Resumo para desenvolvimento: [`CLAUDE.md`](CLAUDE.md).

> Não é blockchain: é uma cadeia de hash replicável. Não é LoRaWAN: é LoRa ponto a ponto. A assinatura protege o **caminho** do dado, não a **medição** (ver Seção 2.3 da especificação).

---

## Começo rápido (sem hardware, 2 minutos)

```bash
git clone https://github.com/viniciusprado17/softwareMNR.git
cd softwareMNR
python3 -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m unittest discover -s tests                 # 56 testes
python run_demo.py                                   # demonstração no terminal
./run_gateway.sh --simulate --demo-controls          # tela em http://127.0.0.1:8000
```

**Windows:** instale o Python 3.12 (marcando "Add python.exe to PATH") e dê **duplo clique em `run_gateway.bat`**: ele instala tudo na primeira vez e abre o navegador. Guia completo, incluindo hardware, celular e por que não usar Vercel: **[`docs/COMO_RODAR.md`](docs/COMO_RODAR.md)**.

Na tela (modo simulado):

1. **Simular aquecimento** → a temperatura passa de 8 °C → ALARME.
2. **Adulterar pacote** → `ASSINATURA INVÁLIDA` (8,6 °C reescrito como 5,0 °C, assinatura original).
3. **Reenviar pacote** → `REPLAY`.
4. **Verificar corrente** (verde) → **Adulterar o banco** → **Verificar corrente** (vermelho, aponta o bloco e o motivo).
5. **Restaurar demo** para a próxima rodada.

---

## Estrutura do repositório

```
src/coldchain/          gateway em Python (roda no Raspberry Pi ou no PC)
  packet.py             formato do pacote v1 (fonte da verdade, 24 + 64 = 88 bytes)
  crypto.py             ECDSA P-256 + SHA-256, assinatura bruta r||s
  decision.py           classificação térmica
  ledger.py             SQLite com cadeia de hash, eventos, verify_chain detalhado
  gateway.py            validações em ordem fixa, status recalculado, silêncio, ressincronização
  serial_bridge.py      ponte serial com o receptor (+ modo --simulate)
  config.py             config.toml e keys/nodes.json
  webapp.py, static/    tela de demonstração (FastAPI, HTML/JS/CSS locais, sem CDN)
  node_sim.py           nó simulado
firmware/
  lib/coldchain_core/   núcleo portátil em C++ (pacote, SHA-256, ECDSA micro-ecc, autoteste)
  include/              pins.h, config.h, keys.example.h (keys.h real fica fora do git)
  node/                 firmware do nó sensor (PlatformIO)
  receiver/             firmware do receptor (PlatformIO)
  vectest/              firmware de teste dos vetores dourados (T4/T5)
  test_host/            o mesmo núcleo compilado no PC e conferido pelo Python
  test_vectors/         vectors.h gerado de tests/vectors.json
tools/                  vetores, provisionamento de chaves, medições, tempo no ar, conferência
tests/                  unittest (Python)
docs/                   especificação, pacote, guia de hardware, medições, artigo x demonstração
deploy/                 serviço systemd do gateway
config.toml             configuração do gateway (sem valores mágicos no código)
```

---

## Comandos úteis

| O que | Comando |
|---|---|
| Testes Python | `python -m unittest discover -s tests` |
| Núcleo do firmware no PC (C++ assina, Python confere) | `bash firmware/test_host/run.sh` |
| Reproduzir os 3 testes do artigo | `python tools/repro_artigo.py` |
| Medir assinatura/verificação no Python (A8) | `python tools/bench_python.py` |
| Tempo no ar teórico (SF7..SF12) | `python tools/airtime.py` |
| Gerar par de chaves de um nó | `python tools/provision_node.py --node-id 1` |
| Regenerar vetores dourados | `python tools/gen_vectors.py && python tools/gen_firmware_vectors.py` |
| Conferir saída serial do firmware | `python tools/check_fw_output.py --port /dev/ttyUSB0` |
| Ponte serial sem tela | `PYTHONPATH=src python -m coldchain.serial_bridge --port /dev/ttyUSB0` |
| Tela com hardware | `./run_gateway.sh --port /dev/ttyUSB0 --demo-controls` |

Passo a passo do hardware (gravar as placas, testes T1–T12, Raspberry Pi): **[`docs/GUIA_HARDWARE.md`](docs/GUIA_HARDWARE.md)**.

---

## API da tela (Seção 10.5)

| Método e rota | Resposta |
|---|---|
| `GET /api/status` | serial, nós (último seq, silêncio), tamanho e cabeça da corrente |
| `GET /api/readings?limit=100` | últimas leituras aceitas |
| `GET /api/events?limit=100` | últimos eventos (aceitos e rejeitados) |
| `GET /api/chain/verify` | `{ok, bloco_invalido, motivo}` |
| `POST /api/demo/tamper` · `replay` · `corrupt-db` · `reset` | só com `--demo-controls` |
| `POST /api/sim/heat` `{"on": true}` | só com `--simulate` |

---

## Estado (19/10/2026)

| Bloco | Situação |
|---|---|
| **A1–A8** (sem hardware) | **Feito.** Ledger estendido, gateway estendido, ponte serial, config, tela, medições Python |
| **Firmware** | Escrito (nó, receptor, vectest). Núcleo testado no PC contra o Python. **Ainda não gravado em placa** |
| **B1–B8** (com hardware) | Aguardando peças (entrega prevista de 30/10 a 10/11). Ver issues e `docs/GUIA_HARDWARE.md` |
| **C1–C4** (extras) | GPS com `env:heltec_v3_node_gps`; MQTT/AWS só se B estiver pronto |

Nada aqui foi medido em hardware ainda. Os números do artigo (14/14, 50/50, 0,59 ms em PC) são da simulação; o tempo de assinatura no ESP32 será medido com o firmware (`INFO,bench_sign_us`). Diferenças entre artigo e protótipo: [`docs/ARTIGO_X_DEMONSTRACAO.md`](docs/ARTIGO_X_DEMONSTRACAO.md).

## Segurança das chaves

- `firmware/include/keys.h`, `keys/private/` e `keys/nodes.json` estão no `.gitignore`. **Nunca** commitar chave privada, certificado ou credencial.
- A chave de `tests/vectors.json` é pública e só serve para teste.
- Se uma chave aparecer em foto, vídeo ou commit: `python tools/provision_node.py --node-id 1 --force` e regravar o nó.

## Equipe

Vinicius Prado Sobral (liderança técnica), Matheus Felipe Pereira Santos, Júlia Lira Santana Rodrigues da Cunha, Manuela Silva Santos Souza, Iasmin Silva de Menezes. Orientador: Prof. Luiz Gomes da Cunha Neto. LACOR — Liga Acadêmica de Computação e Inovação em Robótica, UNIT.
