# Guia de hardware: do pacote dos Correios à demonstração

Roteiro prático do **Bloco B** (Seção 15 da especificação), na ordem certa. Cada etapa tem comando, o que deve aparecer e o que fazer se não aparecer. Marque a issue correspondente só quando o critério passar, com evidência (foto, vídeo ou log).

> Antes de tudo: **antena conectada antes de qualquer transmissão**, **cabo USB-C de dados** (cabo só de carga não aparece na serial), **SHT31-D em 3,3 V, nunca 5 V**. Os pinos em `firmware/include/pins.h` são os usuais da Heltec V3: **confira no pinout oficial da sua revisão** antes de ligar fios.

---

## 0. Instalar as ferramentas (uma vez, no PC de desenvolvimento)

```bash
git clone https://github.com/viniciusprado17/softwareMNR.git && cd softwareMNR
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt          # inclui PlatformIO
pio --version
```

- Alternativa gráfica: VS Code + extensão **PlatformIO IDE**, abrindo cada pasta `firmware/node`, `firmware/receiver`, `firmware/vectest`.
- Linux: `sudo usermod -aG dialout $USER` e fazer logout/login para acessar a porta serial.
- A Heltec V3 usa ponte USB-serial CP2102: no Linux aparece como `/dev/ttyUSB0`, no Windows como `COMx` (instalar o driver CP210x da Silicon Labs se não aparecer).
- As versões estão **fixadas** nos `platformio.ini` (espressif32 6.9.0 = core Arduino-ESP32 2.0.17, RadioLib 6.6.0, micro-ecc num commit fixo). Não atualize sem testar.

A primeira compilação baixa o toolchain do ESP32 (algumas centenas de MB). O CI do GitHub já compila os três firmwares a cada push.

---

## B1. Bring-up das duas placas (T1)

```bash
cd firmware/vectest
pio run -t upload            # grava na placa conectada
pio device monitor           # 115200 baud; Ctrl+C para sair
```

Repita com a segunda placa. **Critério:** as duas aparecem na serial e imprimem `INFO,vectest fw=vectest-1.0`.

Se a placa não aparecer: trocar o cabo; segurar o botão **PRG** (BOOT), apertar **RST**, soltar PRG e gravar de novo.

## B3. Vetores dourados no ESP32 (T4, T5) — fazer ANTES do rádio

Com o `vectest` gravado:

```bash
python tools/check_fw_output.py --vectors --port /dev/ttyUSB0 --seconds 15
```

**Critério:** linhas `VERIFY,...,OK`, `SELFTEST,OK`, e o Python responde `ACEITO` para cada `SIGNED,...` (`falhas=0`). Isso prova que o ESP32 e o gateway falam a mesma língua.

Anote também as linhas `INFO,bench_sign_us,...` e `INFO,bench_verify_us,...` em [`MEDICOES.md`](MEDICOES.md): **é o tempo de assinatura no ESP32** que substitui os 0,59 ms do PC no artigo.

## B2. Sensor e OLED (T2, T3)

Ligação do SHT31-D (Seção 5.3): VIN→3V3, GND→GND, SDA→GPIO 41, SCL→GPIO 42 (Wire1). LED de alarme: GPIO 4 → resistor 220 Ω → LED → GND.

1. Gerar a chave do nó (uma vez; cria `firmware/include/keys.h`, fora do git):

   ```bash
   python tools/provision_node.py --node-id 1
   ```

2. Gravar o nó:

   ```bash
   cd firmware/node
   pio run -e heltec_v3_node -t upload && pio device monitor
   ```

   Sem o sensor ainda? Use `-e heltec_v3_node_fake_sensor` (temperatura falsa oscilando de 1 a 9 °C) para seguir com rádio e assinatura. **Declarar** se for usado em qualquer vídeo.

**Critério:** OLED mostra `NO 1 seq N`, temperatura ambiente plausível e o status. Mão no sensor sobe a temperatura; gelo em saquinho desce. LED **fixo** em ALARME, **piscando** em ALERTA.

Problemas comuns: OLED apagado → Vext (GPIO 36) precisa estar em nível baixo (o firmware faz isso); `ERR,sensor` → conferir fios, endereço 0x44/0x45 e se 41/42 estão livres na sua placa.

## B4. LoRa nó → receptor (T6)

Na segunda placa:

```bash
cd firmware/receiver
pio run -t upload && pio device monitor
```

**Critério:** a cada 10 s aparece `RX,<rssi>,<snr>,<176 caracteres hex>` (88 bytes) e o OLED do receptor mostra a contagem.

Se `ERR,<código>,radio.begin falhou`: o suspeito nº 1 é o **TCXO** (`LORA_TCXO_V` em `firmware/include/config.h`, padrão 1,8 V) e o **DIO2 como chave RF**. Compare com o exemplo oficial da Heltec/RadioLib para a V3. Se nada chega: parâmetros de rádio diferentes entre as placas (devem ser idênticos, todos em `config.h`), antena solta, ou placas muito próximas (afaste 1–2 m).

Conferir os pacotes recebidos no Python:

```bash
python tools/check_fw_output.py --port /dev/ttyUSB0 --seconds 30
```

## B5. Nó completo com `seq` na NVS (T9)

Desligue e religue o nó algumas vezes. **Critério:** `INFO,seq_inicial=N` continua de onde parou e o gateway **não** acusa `replay`.

Plano de emergência (só se o `seq` se perder): `./run_gateway.sh --port /dev/ttyUSB0 --reset-node 1` registra um bloco de ressincronização. Fica desligado por padrão; diga que existe se perguntarem.

## B6. Integração ponta a ponta (T7, T8, T10)

### Raspberry Pi (gateway)

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/viniciusprado17/softwareMNR.git && cd softwareMNR
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
sudo usermod -aG dialout $USER   # logout/login depois
```

Copie `keys/nodes.json` do PC onde rodou o `provision_node.py` para o Pi (só a chave **pública**; nunca copie `keys.h` ou `keys/private/` para lugar público).

```bash
./run_gateway.sh --port /dev/ttyUSB0 --demo-controls --host 0.0.0.0
```

Abra `http://<ip-do-pi>:8000` no notebook. **Critério:** pacotes reais `ACEITO`; **Adulterar pacote** → `ASSINATURA INVÁLIDA`; **Reenviar pacote** → `REPLAY`; **Adulterar o banco** + **Verificar corrente** → bloco apontado em vermelho. Roteiro completo em menos de 5 minutos.

Subir sozinho ao ligar o Pi: ver `deploy/coldchain-gateway.service`.

## B7. Medições para o artigo (Seção 12.4)

Preencher [`MEDICOES.md`](MEDICOES.md):

- Tempo de assinatura no ESP32: `INFO,bench_sign_us` (vectest e nó, n = 100).
- Tempo no ar: teórico com `python tools/airtime.py`; medido no nó em `INFO,...,tx_us=`.
- Tempo de verificação no gateway: `python tools/bench_python.py` **rodando no Raspberry Pi**.
- Taxa de entrega e RSSI/SNR em 1 m, 5 m e através de parede: contar `aceito` nos eventos contra o `seq` enviado.
- Detecção de adulteração com hardware: clicar **Adulterar pacote** 50 vezes (ou script) e contar.

## B8. Ensaio de 30 minutos (T11, T12)

Deixar tudo ligado 30 min. **Critério:** sem travar, sem perda sistemática (o evento `silencio` não pode aparecer). Registrar no relatório.

---

## Plano B / Plano C (Seção 17)

- **5/11 é a data de corte.** Se o hardware não funcionar: `./run_gateway.sh --simulate --demo-controls` (a tela avisa "Modo simulado") + vídeo + tabela [`ARTIGO_X_DEMONSTRACAO.md`](ARTIGO_X_DEMONSTRACAO.md), dizendo claramente que o protótipo físico está em desenvolvimento.
- **Parcial:** mostrar o que funciona e usar o simulador para o resto, identificando na tela o que é real e o que é simulado.
