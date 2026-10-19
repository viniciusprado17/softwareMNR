# Como rodar o sistema no seu PC

A tela do gateway roda **localmente**, no seu computador ou no Raspberry Pi. Ela não precisa de internet depois de instalada, e isso é proposital: no evento o Wi-Fi pode ser ruim e o receptor LoRa fica ligado por **cabo USB** ao computador.

## Windows (mais fácil)

1. Instale o **Python 3.12** em https://www.python.org/downloads/ e **marque "Add python.exe to PATH"** na primeira tela do instalador.
2. Baixe o projeto: no GitHub, botão verde **Code → Download ZIP**, e extraia. Se tiver Git, use `git clone https://github.com/viniciusprado17/softwareMNR.git`.
3. Dê **duplo clique em `run_gateway.bat`**.
   - Na primeira vez ele cria o ambiente e instala as dependências, o que leva 1 a 2 minutos.
   - O navegador abre sozinho em **http://127.0.0.1:8000** no modo simulado.
4. Para parar, feche a janela preta ou aperte `Ctrl+C` nela.

Com o receptor Heltec no USB, descubra a porta no **Gerenciador de Dispositivos → Portas (COM e LPT)**, por exemplo "Silicon Labs CP210x (COM5)", e rode no terminal, dentro da pasta:

```bat
run_gateway.bat --port COM5 --demo-controls
```

Se a porta não aparecer, instale o driver **CP210x** da Silicon Labs e use um cabo USB-C **de dados**.

## Linux / macOS / Raspberry Pi

```bash
git clone https://github.com/viniciusprado17/softwareMNR.git && cd softwareMNR
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
./run_gateway.sh --simulate --demo-controls          # sem hardware
./run_gateway.sh --port /dev/ttyUSB0 --demo-controls # com o receptor (macOS: /dev/cu.usbserial-*)
```

Abra http://127.0.0.1:8000.

## Abrir no celular ou em outro notebook

Ligue os dois aparelhos na **mesma rede**, que pode ser o roteador do celular, e rode:

```bat
run_gateway.bat --simulate --demo-controls --host 0.0.0.0
```

Descubra o IP do PC com `ipconfig` (Windows) ou `hostname -I` (Linux) e abra `http://<IP>:8000` no celular. O Windows pode pedir para liberar o firewall: aceite para "Redes privadas".

## Roteiro da demonstração na tela

1. **Simular aquecimento**: a temperatura passa de 8 °C e aparece ALARME. Com hardware real, aqueça o sensor com a mão.
2. **Adulterar pacote**: aparece `ASSINATURA INVÁLIDA`.
3. **Reenviar pacote**: aparece `REPLAY`.
4. **Verificar corrente** (verde), depois **Adulterar o banco**, depois **Verificar corrente** de novo: fica vermelho e aponta o bloco adulterado.
5. **Restaurar demo** antes da próxima rodada.

No modo simulado a tela mostra "Modo simulado: os pacotes não vêm do hardware". Diga isso à banca se usar esse modo (Plano B).

## Por que não hospedar na Vercel (ou outra nuvem)?

- A Vercel roda funções que **desligam entre uma requisição e outra**. O gateway precisa ficar ligado o tempo todo lendo a porta USB e guardando a corrente no SQLite, e isso não funciona lá.
- O receptor LoRa está **fisicamente no USB** do seu PC ou do Pi. Um servidor na nuvem não enxerga essa porta.
- A demonstração deve funcionar **sem internet** (Seção 17, risco "Wi-Fi ruim no local").

Se quiser mostrar os dados também na nuvem, o caminho é a Camada 3: o gateway local publica as leituras aceitas por MQTT/AWS IoT (issue #10). Isso é extra, e a demonstração principal continua local.
