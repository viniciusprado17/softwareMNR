# Prompt para a sessão no notebook (MNR 2026)

Como usar: (1) no notebook, abra o PowerShell e rode o comando do "PASSO ZERO" abaixo (instala tudo e clona o projeto); (2) abra o app do Claude, aba Code, na pasta C:SERS<USUARIO>PROJETOSSOFTWAREMNR E COLE O BLOCO DE TEXTO.

```text
Título da sessão: MNR 2026 no notebook: placas, gateway e demonstração

PASSO ZERO (fazer antes de tudo)
1. Clonar o repositório público: git clone -b main https://github.com/viniciusprado17/softwareMNR.git
   (se o Git não existir: winget install -e --id Git.Git, e me avise).
   ATENÇÃO: use o ramo main. O ramo padrão do GitHub está num ramo antigo (claude/...), 11 commits atrás.
2. Trabalhar SEMPRE dentro da pasta softwareMNR. Este é o notebook que vai para a fase nacional,
   então tudo da demonstração precisa rodar aqui.
3. Ler, nesta ordem: CLAUDE.md, docs/ESPECIFICACAO.md (Seções 15 e 16 e o plano A1..B8),
   docs/GUIA_HARDWARE.md, docs/DECISOES.md, docs/ARTIGO_X_DEMONSTRACAO.md, docs/MEDICOES.md
   e firmware/include/pins.h.

CONTEXTO
- Projeto MNR 2026 (LACOR/UNIT). Fase nacional em João Pessoa, 23 a 29/11/2026. Restam poucos
  dias: priorize o que aparece na demonstração.
- O núcleo em Python (pacote de 88 bytes, ECDSA P-256, ledger com cadeia de hash, gateway, tela
  web) está pronto e testado. O firmware (firmware/node, receiver, vectest) compila no CI, mas
  NUNCA foi gravado em placa.
- Hardware: 2x Heltec WiFi LoRa 32 V3, 2x SHT31-D, 1x GPS NEO-6M. Pinos da Heltec e do SHT31-D
  já soldados. A Heltec liga com a antena LoRa conectada e o OLED acende. O GPS NÃO está
  soldado: GPS é opcional, não dependa dele.
- Ainda não tenho fios/jumpers para o sensor. Quando chegar a hora, diga exatamente quais fios
  e de que tipo, e espere eu confirmar.
- Alimentação pela USB do notebook. Windows: porta COMx; se não aparecer, driver CP210x da
  Silicon Labs.
- Não domino eletrônica nem solda. Explique em linguagem simples, um passo de cada vez, e avise
  antes de qualquer ação física arriscada.

O QUE JÁ FOI FEITO EM OUTRO PC (16/11), PARA VOCÊ NÃO REPETIR À TOA
- No PC de mesa: Python 3.12 instalado via winget, requirements-dev.txt instalado, PlatformIO
  6.2.0 ok, "python -m unittest discover -s tests" passou com 68 testes no ramo main (o CLAUDE.md ainda diz
  56: corrigir no fechamento), firmware/vectest compilou (a primeira compilação baixa o
  toolchain do ESP32-S3 e leva uns 5 minutos). Nada foi gravado em placa.
- Lições do PC: o Python do winget não entrou no PATH. Se "python" ou "pio" não funcionarem,
  use o caminho completo (%LOCALAPPDATA%\Programs\Python\Python312\python.exe) e chame o
  PlatformIO como "python -m platformio". Instalar com:
  winget install -e --id Python.Python.3.12 --scope user
- pins.h ainda NÃO foi conferido contra o pinout oficial da revisão da minha Heltec V3. Fazer
  isso antes de pedir qualquer ligação (sensor previsto em Wire1, SDA 41 e SCL 42; OLED no
  Wire padrão, 17 e 18; Vext no 36 em nível baixo).

REGRAS DE SEGURANÇA DO HARDWARE (não negociáveis)
1. Antena conectada antes de qualquer transmissão LoRa.
2. Cabo USB-C de dados (cabo só de carga não aparece na serial).
3. SHT31-D sempre em 3,3 V, nunca 5 V.
4. Conferir firmware/include/pins.h contra o pinout oficial da minha revisão da Heltec V3 antes
   de pedir qualquer ligação. O OLED usa o I2C padrão, então o sensor vai em outros pinos
   (Wire1). Se houver dúvida, pare e me pergunte.
5. Não existe peça reserva. Não arrisque as placas com testes improvisados.

REGRAS DE CÓDIGO E HONESTIDADE
- Não comitar firmware/include/keys.h, keys/nodes.json com chaves, chaves privadas, .pem, .key
  ou credenciais. O repositório é público. Antes de cada commit, rode "git status" e confira.
- Um commit por tarefa, com mensagem clara. Antes de mudar o formato do pacote, atualize
  docs/PACOTE.md e os testes. Não mude o formato do pacote nem a curva (P-256) sem me avisar.
- Comentários e documentos em português, código em inglês. Sem travessões nos textos que eu
  for apresentar.
- O artigo aprovado só tem simulação em Python. Nunca declare na demonstração ou nos documentos
  algo que não tenha sido medido de verdade. Registre cada medição real em docs/MEDICOES.md,
  com data, e atualize docs/ARTIGO_X_DEMONSTRACAO.md quando algo mudar.
- A latência de 0,59 ms do artigo foi medida em Python no PC. A do ESP32 tem que ser medida de
  verdade e anotada como medição nova.

PLANO (siga a ordem, uma etapa por vez, só avance quando o critério passar)
E0. Preparar o notebook: Git, Python 3.10+, "pip install -r requirements-dev.txt" (inclui
    PlatformIO), "pio --version" e os testes (68 devem passar no main). Compile firmware/vectest já,
    antes de eu plugar a placa. Se faltar algo, instale e me avise.
E1. B1, bring-up das duas placas: gravar firmware/vectest em cada Heltec
    ("pio run -t upload" e "pio device monitor" a 115200, com --upload-port/--port COMx se
    preciso). Critério: as duas imprimem "INFO,vectest fw=vectest-1.0". Se a placa não
    aparecer: trocar o cabo; segurar PRG, apertar RST, soltar PRG e gravar de novo.
E2. B3, vetores dourados no ESP32: "python tools/check_fw_output.py --vectors --port COMx
    --seconds 15". Critério: VERIFY OK, SELFTEST,OK e falhas=0 (assinaturas e hashes batem com
    o Python). Anotar INFO,bench_sign_us e bench_verify_us em docs/MEDICOES.md. ANTES do rádio.
E3. Sensor: escrever e gravar um scanner I2C no Wire1 (conferindo os pinos). Eu faço a ligação
    quando você disser quais fios. Critério: o scanner enxerga o SHT31-D (0x44 ou 0x45).
E4. Temperatura e umidade do SHT31-D no OLED, com a regra de decisão (OK, ALERTA, ALARME,
    faixa 2 a 8 °C) e o LED da placa. Critério: aquecer o sensor com a mão muda o estado.
E5. Nó assinando de verdade: "python tools/provision_node.py --node-id 1" (gera keys.h, fora do
    git) e firmware/node com leitura, pacote de 88 bytes e assinatura micro-ecc. Critério: o
    pacote do firmware passa no Gateway sem alteração.
E6. Rádio, só depois do E5: LoRa 915 MHz entre placa nó e placa receptor (receiver imprime
    RX,<rssi>,<snr>,<hex>). Critério: o gateway aceita o pacote vindo do ar.
E7. Ponta a ponta no notebook: receptor por USB, serial_bridge, gateway e tela web
    (run_gateway.bat) com leituras reais. Testar adulteração, replay e verificação da corrente
    (botões de ataque da tela). Critério: tudo funciona com dados reais.
E8. Medições para a banca: latência de assinatura no ESP32, alcance simples, taxa de pacotes
    recebidos. Registrar em docs/MEDICOES.md só o que foi medido.
E9. Fechamento: atualizar CLAUDE.md (estado do código, o que foi gravado em placa, número de
    testes), docs/ARTIGO_X_DEMONSTRACAO.md e o roteiro de demonstração de 5 minutos. Rodar os
    testes de novo e conferir o CI.

PLANO B (se algo travar)
- Rádio não funciona a tempo: sensor real + assinatura no nó + gateway por USB (camada 1) e a
  simulação de rádio no modo --simulate, declarando isso com clareza.
- Sensor não funciona: modo simulado (run_gateway.bat --simulate --demo-controls) e hardware
  mostrado como "em integração".
- Corte de escopo de trás para frente: MQTT/AWS e GPS primeiro, depois a tela, por último o
  pacote assinado.

COMO TRABALHAR COMIGO
- No início de cada etapa, diga qual é e quanto tempo estima. Ao terminar, mostre o critério
  de aceite que passou (saída da serial, teste verde ou log) e o que vem a seguir.
- Se um passo exigir ação física minha (ligar fio, apertar botão, plugar cabo), diga de forma
  bem objetiva e espere eu responder "feito".
- Erro de compilação, de pino ou de driver: explique em uma frase e proponha a correção.
- Ao final de cada sessão, deixe o CLAUDE.md com o estado atual e o próximo passo, e dê push.

Comece agora pelo PASSO ZERO e pelo E0.
```
