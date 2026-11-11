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

### QR code e app no celular

Com a tela aberta, clique em **Celular** (canto superior direito): aparece um QR code. A aba **Painel** leva ao endereço desta tela e a aba **Montagem 3D** leva à simulação ilustrativa da montagem (precisa de internet).

- O QR do painel só funciona se o servidor escutar na rede, então rode com `--host 0.0.0.0` (como acima). Sem isso a tela avisa o que fazer.
- No link público do Render o QR já aponta para o endereço certo.
- **Instalar como app:** no celular, abra o endereço no Chrome (Android: menu → *Instalar app*) ou no Safari (iPhone: *Compartilhar → Adicionar à Tela de Início*). O app guarda só a casca da tela; os dados sempre vêm do gateway, então sem rede ele mostra "gateway fora do ar". Em rede local (sem HTTPS) o navegador pode oferecer só o atalho, sem o modo offline da casca.

### Verificador independente

Botão **Verificador** no topo (ou `http://127.0.0.1:8000/verificador`). O navegador baixa a corrente, refaz cada hash e confere cada assinatura ECDSA sozinho, sem confiar no gateway. **Simular adulteração** inverte 1 bit de um bloco só na memória da página (o gateway não muda) e mostra a falha no bloco certo. **Baixar export** gera o arquivo `.json`, que pode ser conferido depois em qualquer computador com a mesma página.

## Roteiro da demonstração na tela

1. **Simular aquecimento**: a temperatura passa de 8 °C e aparece ALARME. Com hardware real, aqueça o sensor com a mão.
2. **Adulterar pacote**: aparece `ASSINATURA INVÁLIDA`.
3. **Reenviar pacote**: aparece `REPLAY`.
4. **Verificar corrente** (verde), depois **Adulterar o banco**, depois **Verificar corrente** de novo: fica vermelho e aponta o bloco adulterado.
5. **Bateria do artigo**: 14/14 classificações e 50/50 adulterações rejeitadas, reproduzindo os testes 1 e 2 do artigo, sem mexer na corrente real.
6. **Verificador** (topo): a corrente conferida no navegador, sem confiar no gateway.
7. **Restaurar demo** antes da próxima rodada.

No modo simulado a tela mostra "Modo simulado: os pacotes não vêm do hardware". Diga isso à banca se usar esse modo (Plano B).

## Link para a equipe pela internet

O **modo simulado** pode ser publicado com link fixo e senha no Render: ver [`LINK_EQUIPE.md`](LINK_EQUIPE.md). O modo com as placas continua local.

## Por que não na Vercel, e por que o hardware fica local?

- A Vercel roda funções que **desligam entre uma requisição e outra** (o Render mantém um servidor ligado, por isso serve para o modo simulado). O gateway precisa ficar ligado o tempo todo lendo a porta USB e guardando a corrente no SQLite, e isso não funciona lá.
- O receptor LoRa está **fisicamente no USB** do seu PC ou do Pi. Um servidor na nuvem não enxerga essa porta.
- A demonstração deve funcionar **sem internet** (Seção 17, risco "Wi-Fi ruim no local").

Se quiser mostrar os dados também na nuvem, o caminho é a Camada 3: o gateway local publica as leituras aceitas por MQTT/AWS IoT (issue #10). Isso é extra, e a demonstração principal continua local.
