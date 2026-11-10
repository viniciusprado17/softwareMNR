# Tarefa "Maximização" (entrega única para o Fable)

> **Para quem executa:** este arquivo é a tarefa inteira. Leia-o uma vez, de cima a baixo, e execute as Partes 1 a 3 em ordem (a Parte 4 é opcional). Não precisa de mais contexto do que está aqui. Cada token conta: siga as **Regras de custo**.
>
> **Para o Claude principal:** só dispare isto quando o usuário disser **COMEÇAR MAXIMIZAÇÃO**. Antes: `bash tools/fable_preflight.sh` (tudo OK) e `git push` (branch igual ao remoto). Procedimento completo no fim deste arquivo.

## 0. Regras de custo (obrigatórias)

1. **Leia só o que a parte pede** ("Ler"). Não varra o repositório. Não leia `docs/ESPECIFICACAO.md` inteiro (1040 linhas): só as linhas indicadas. Nunca leia `static/vendor/*`, `docs/*.pdf`, `firmware/.host_build`.
2. **Sem capturas de tela.** A revisão visual é do Claude principal. Valide páginas pelo DOM (Playwright, `page.textContent`) e por `pageerror`/`console error` vazios.
3. **Sem pesquisa na web, sem instalar bibliotecas novas** (nem pip, nem npm, nem CDN). Tudo com a biblioteca padrão, FastAPI/cryptography já instalados e `static/vendor/qrcode.js`.
4. **Não faça polling do CI.** Ao terminar a Parte 3 (e a 4, se feita), dê `git push` e encerre; o Claude principal confere o CI.
5. **Um commit por parte**, mensagem em português, terminando com as duas linhas de atribuição que o ambiente exige. Push só no fim (ver "Entrega").
6. **Bloqueado por mais de 2 tentativas na mesma coisa? Pare essa parte**, anote no relatório o erro exato e siga para a próxima parte independente (a Parte 2 e a 3 não dependem da 1).
7. **Não refatore nada fora do pedido.** Sem renomear, sem reformatar arquivos existentes, sem mexer em `firmware/lib/coldchain_core`, `firmware/node`, `firmware/receiver`, `firmware/vectest` (só ler, se preciso).

## 1. Contexto mínimo

Projeto MNR 2026 (LACOR/UNIT): nó ESP32 (Heltec WiFi LoRa 32 V3) mede temperatura, decide OK/ALERTA/ALARME, **assina** a leitura com ECDSA P-256 + SHA-256 e transmite por LoRa 915 MHz. O gateway (Python, `src/coldchain/`) verifica a assinatura, rejeita adulteração e replay e grava numa corrente de hash em SQLite. A tela web (`src/coldchain/webapp.py` + `static/`) mostra tudo; roda sem hardware com `--simulate`. As placas **chegam montadas na sexta, 13/11**; o evento é de 23 a 29/11. O objetivo da Maximização: **deixar a bancada de sexta pronta** (Parte 1) e **dar à banca funcionalidades que provem a segurança** (Partes 2 a 4).

**Regras do projeto (inegociáveis):**
- Código em **inglês**; comentários e docs em **português**.
- **Não afirmar na tela ou nos docs nada que não tenha sido medido.** O artigo aprovado só tem simulação em Python; hardware é "planejado". Tudo que for simulado precisa estar rotulado como simulado. Latência do artigo (0,59 ms) foi em Python no PC: **não** repita esse número como se fosse do ESP32.
- Não chame a corrente de "blockchain" (é cadeia de hash replicada).
- **Não mude o formato do pacote** (`docs/PACOTE.md`: payload 24 B + assinatura r‖s 64 B = 88 B, big-endian).
- Toda rota nova ou campo novo na API precisa entrar na tabela da **Seção 10.5** de `docs/ESPECIFICACAO.md` (linhas ~721 a 738) **e** ter teste.
- Antes de cada commit: `PYTHONPATH=src python -m unittest discover -s tests` (hoje: **61 testes, OK**). Nunca reduza esse número.

**Ambiente:**
- Python: `/tmp/claude-0/venv/bin/python` (ou `.venv/bin/python`); testes: `PYTHONPATH=src /tmp/claude-0/venv/bin/python -m unittest discover -s tests`. Subir a tela: `PYTHONPATH=src python -m coldchain.webapp --simulate --demo-controls --db :memory: --web-port 8000`.
- Node 22 (tem `crypto.subtle`, `node --test`). Playwright: `NODE_PATH=$(npm root -g) node script.js`.
- **O PlatformIO não consegue baixar nada nesta máquina** (registro bloqueado): o firmware **não compila aqui**. A prova do firmware é o CI do GitHub. Por isso, na Parte 1, escreva código conservador espelhando o que já compila em `firmware/node/src/`, e diga no relatório que a compilação está **não verificada localmente**.
- Estilos da tela: variáveis CSS em `static/style.css` (`--panel`, `--accent`, `--ok`, `--bad`…); fontes e ícones já locais. Reuse; não crie sistema novo.

## Parte 1: Kit de bancada para sexta (`firmware/bench`)

**Objetivo.** Na sexta, logo depois de soldar, o usuário precisa testar cada etapa **isoladamente** (etapas 4 a 7 do PDF "Projeto Etapas MNR2026": teste de vida, sensor, estado no display, rádio), sem depender da assinatura nem de chaves. Hoje só existem `node`, `receiver` e `vectest`; o `node` mistura tudo.

**Ler:** `firmware/include/pins.h`, `firmware/include/config.h`, `firmware/node/platformio.ini`, `firmware/node/src/display.{h,cpp}`, `sensor.{h,cpp}`, `radio.{h,cpp}`, `firmware/receiver/src/main.cpp` (só a inicialização do rádio), `firmware/test_host/run.sh` (só para ver o padrão), `.github/workflows/ci.yml` (job `firmware-build`), `docs/GUIA_HARDWARE.md` (inteiro; é curto).

**Criar** o projeto PlatformIO `firmware/bench/` com **as mesmas versões fixas** de plataforma e bibliotecas do `firmware/node/platformio.ini`, `lib_dir = ../lib`, `include_dir = ../include`, e **sem `default_envs`** (assim `pio run -d firmware/bench` compila todos). Cinco ambientes, um sketch por ambiente (`build_src_filter`), cada um **imprimindo na serial a 115200 linhas com prefixo estável** e mostrando o essencial no OLED:

| env | Etapa do PDF | Comportamento exato |
|---|---|---|
| `lifetest` | 4 | Liga Vext (`VEXT_CTRL` em nível baixo), reseta o OLED, mostra "VIVO" + contador de segundos, pisca `BOARD_LED`. Serial: `LIFE,<segundos>` a cada 1 s. |
| `i2cscan` | 5 | Varre `0x08..0x77` no barramento `Wire1` com `SENSOR_SDA/SENSOR_SCL` de `pins.h` a cada 3 s. Serial: `I2C,found,0x44` por endereço, ou `I2C,none`. OLED mostra os endereços. **Comando serial** `scan <sda> <scl>` reinicia o `Wire1` em outros pinos e varre (para o caso de 41/42 não estarem livres: o usuário digita os pinos do pinout oficial; **não invente lista de pinos candidatos**). Rejeite pinos que já são usados em `pins.h` e os GPIO 19 e 20 (USB). |
| `sensor` | 5 e 6 | Lê o SHT31 em `Wire1` (endereço `SHT31_ADDR`; tente 0x45 se 0x44 falhar) a cada 2 s. Classifica com `TEMP_LOW_C`, `TEMP_HIGH_C`, `TEMP_MARGIN_C` (mesma regra do `node`: alarme acima de 8 °C ou abaixo de 2 °C, alerta a 0,5 °C do limite; **reuse a função que o `node` já usa**, não reescreva a regra). OLED: temperatura grande, umidade, estado OK/ALERTA/ALARME; LED externo `ALARM_LED` acende no ALARME. Serial: `SENS,<temp_c>,<hum_pct>,<OK\|ALERTA\|ALARME>` ou `ERR,sensor`. |
| `ping_tx` | 7 | Rádio como no `node` (915 MHz, SF7, BW 125, TCXO 1,8 V de `config.h`). Envia `PING,<n>` a cada 2 s. OLED: "TX n". Serial: `TX,<n>` ou `ERR,radio,<codigo>`. |
| `ping_rx` | 7 | Recebe e mostra no OLED a mensagem, RSSI e SNR. Serial: `RX,<rssi>,<snr>,<texto>`. |

Nenhum ambiente usa `keys.h` nem assina. O usuário **não grava nada ainda** (sem hardware aqui).

**Alterar:**
- `.github/workflows/ci.yml`: adicionar `bench` à matriz `project: [node, receiver, vectest, bench]` do job `firmware-build` (o passo `pio run -d firmware/${{ matrix.project }}` já serve).
- `docs/GUIA_HARDWARE.md`: nova seção **"Roteiro de bancada (sexta)"**, uma subseção por ambiente: comando `pio run -d firmware/bench -e <env> -t upload && pio device monitor`, a saída serial esperada (linhas acima), e o critério **"deu certo quando"** copiado do PDF (display mostra texto; temperatura coerente e sobe com a mão; receptor mostra mensagens a poucos cm e depois a alguns metros). Inclua "se der errado" curto (cabo de dados, driver, antena, pinos, endereço 0x45). Diga em uma linha que **a compilação foi verificada só pelo CI**.

**Aceite (Parte 1):** arquivos criados; `grep -R "keys.h" firmware/bench` vazio; `python -m unittest` ainda 61 OK; `docs/GUIA_HARDWARE.md` com a seção. Compilação: **declarar não verificada localmente**.
**Não fazer:** mexer em `pins.h` (se achar um pino errado, **anote no relatório**, não corrija); inventar pinos; incluir assinatura/LoRa no `sensor`.

## Parte 2: Verificador independente no navegador

**Objetivo.** Provar que **quem recebe o laudo não precisa confiar no gateway**: o navegador refaz a corrente de hash e confere cada assinatura ECDSA P-256 com WebCrypto. O formato do projeto (r‖s bruto, chave pública X9.62 não comprimida de 65 bytes `04‖X‖Y`) é exatamente o que o WebCrypto aceita (`importKey("raw", …, {name:"ECDSA", namedCurve:"P-256"})` e `verify({name:"ECDSA", hash:"SHA-256"}, key, sig, payload)`). **Já testado**: os 6 vetores de `tests/vectors.json` batem (4 válidos aceitos, 2 inválidos de propósito rejeitados).

**Ler:** `src/coldchain/ledger.py` linhas 25 a 80 e 201 a 250 (regras exatas de hash e verificação), `src/coldchain/crypto.py` (`public_bytes_raw`), `src/coldchain/webapp.py` (como as rotas são montadas; adicione perto de `/api/chain/verify` e de `index`), `tests/test_webapp.py` (padrão de teste), `tests/vectors.json` (estrutura), `docs/ESPECIFICACAO.md` linhas 696 a 738.

**Regras que o verificador JS deve reproduzir (paridade com `Ledger.verify_chain`, mesma ordem, mesmos motivos):**
1. `GENESIS` = 32 bytes zero; `prev_hash` do bloco deve ser o `hash` do anterior → senão `prev_hash_diferente`.
2. `hash == SHA256(prev_hash ‖ payload ‖ sig)` → senão `hash_quebrado`.
3. Bloco `kind="data"`: assinatura válida com a chave do `node_id` → senão `assinatura_invalida` (nó sem chave também é `assinatura_invalida`).
4. Bloco `kind="resync"`: `sig` vazia, `seq == 0` e payload `RESYNC` (6 bytes) + `node_id` (u16) + `rx_ts` (u32), com `node_id` igual ao do bloco; senão `coluna_divergente`.
5. Devolve o **primeiro** bloco inválido: `{ok, bad_idx, reason}` (`coluna_divergente` só para o caso do item 4: o export não traz colunas decodificadas).
**Não adicione verificações que o Python não faz.** Informação extra (temperatura decodificada, estado) pode ser exibida, mas não muda o veredito.

**Criar:**
- **Rota** `GET /api/export/chain` em `webapp.py`: `{"format":"coldchain-export/1","curve":"P-256","genesis":"<64 hex>","nodes":{"<node_id>":"<130 hex, chave pública>"},"head":"<hex>","blocks":[{"idx","kind","node_id","seq","rx_ts","prev_hash","payload","sig","hash"}]}` (tudo em hex minúsculo, todos os blocos, em ordem). `?download=1` acrescenta `Content-Disposition: attachment; filename="corrente_<data>.json"`. Chaves vêm de `gateway.keys` via `crypto.public_bytes_raw`.
- **Módulo puro** `src/coldchain/static/verifier-core.js` (sem DOM, funciona no navegador e no Node 22): `export async function verifyExport(doc, subtle = globalThis.crypto.subtle)` → `{ok, checked, bad: {idx, reason}|null, blocks: [{idx, ok, reason}]}`. Carregado na página como `<script type="module">`.
- **Página** `src/coldchain/static/verificador.html` + `verificador.js`, servida em `GET /verificador` (rota como a do `index`). Visual igual ao da tela principal (mesmos tokens CSS e fontes; link para `/static/style.css`). Conteúdo: título "Verificador independente"; botões **Carregar do gateway** (busca `/api/export/chain`), **Abrir arquivo .json**, **Baixar export**; veredito grande (`#verdict`: "CORRENTE ÍNTEGRA · N blocos" ou "QUEBRADA no bloco X: motivo"); lista de blocos com ✓/✗; botão **Simular adulteração (só no navegador)** que inverte 1 bit do payload de um bloco **em memória** e reverifica, com aviso "o gateway não foi alterado". Texto fixo explicando: "Esta conferência roda no seu navegador; a chave pública vem do export; não depende do gateway estar honesto" e a ressalva honesta: **"As chaves públicas vêm do próprio arquivo; para confiança total, compare a chave com a registrada no momento da instalação do nó."**
- No `index.html`: um link "Verificador" no topo (ao lado de "Montagem 3D"), mesmo estilo `btn ghost sm`.
- **Gerador de casos** `tools/gen_verifier_fixtures.py` → `tests/fixtures/verifier_cases.json`: usa o `Ledger`/`Gateway` reais para montar cadeias e gravar, para cada caso, o `doc` exportado **e** o resultado de `Ledger.verify_chain(keys)` (`ok`, `bad_idx`, `reason`). Casos: cadeia válida (5 blocos); payload alterado; `prev_hash` alterado; `hash` alterado; assinatura com 1 bit trocado; bloco de nó desconhecido; cadeia com bloco `resync` válido; `resync` adulterado. **Gere o JSON e commite-o.**
- **Teste de paridade** `tests/js/verifier.test.mjs` (`node --test tests/js/`): para cada caso, `verifyExport(doc)` deve dar exatamente o mesmo `ok/bad_idx/reason` que o Python gravou. Mais um teste com `tests/vectors.json`: o JS aceita os 4 vetores `valid` e rejeita os 2 `invalid`.
- **Teste Python** da rota (`tests/test_webapp.py`): formato do export; `head` igual ao `/api/status`; `nodes` com chave de 130 hex; `?download=1` com o cabeçalho; e **round-trip**: o export de uma cadeia simulada passa no `Ledger.verify_chain`-equivalente (use os mesmos campos).
- CI (`.github/workflows/ci.yml`): job `verificador-js` (`actions/setup-node@v4` com node 22; `python tools/gen_verifier_fixtures.py && git diff --exit-code tests/fixtures/verifier_cases.json && node --test tests/js/`).
- Docs: Seção 10.5 (duas linhas novas: `GET /api/export/chain` e a página `GET /verificador`); `docs/COMO_RODAR.md` (um parágrafo curto "Verificador independente").
- `sw.js`: **não** cache `/api/export/chain` (já ignora `/api/*`; só confirme). Pode acrescentar `/verificador` e `/static/verifier-core.js` ao `SHELL`.

**Aceite (Parte 2):** testes Python (61 + novos) OK; `node --test tests/js/` OK; Playwright (sem imagem): com a tela simulada no ar e ≥ 8 blocos, abrir `/verificador`, clicar "Carregar do gateway" e `#verdict` contém "ÍNTEGRA"; clicar "Simular adulteração" e `#verdict` contém "QUEBRADA"; zero `pageerror`.
**Não fazer:** nenhuma biblioteca criptográfica nova; não mexer em `ledger.py`/`crypto.py`; não transformar o export em formato "oficial" além do descrito.

## Parte 3: Bateria do artigo, prova do hash e métricas de cadeia de frio

**3a. Bateria "do artigo" ao vivo.** Ler `tools/repro_artigo.py` inteiro e `src/coldchain/decision.py`.
- Rota `POST /api/demo/battery` (**só com `--demo-controls`**, como as outras `/api/demo/*`). Reproduz os testes 1 e 2 do artigo **sem tocar na corrente nem nos eventos reais** (use um `Ledger(":memory:")`/`Gateway` descartável com um par de chaves de teste gerado na hora): Teste 1: 14 temperaturas de 2 a 15 °C, limiar 8 °C → quantas classificadas corretamente; Teste 2: 50 adulterações do campo temperatura após assinar → quantas rejeitadas pelo gateway descartável. Resposta: `{"classification":{"total":14,"correct":14},"tamper":{"total":50,"rejected":50,"accepted":0},"note":"..."}`. `note` fixa: "Mesmos testes da simulação do artigo (Tabela 2), executados agora neste computador com chave de teste. A latência do artigo não é medida aqui."
- **Teste obrigatório:** depois da bateria, `/api/status` tem os mesmos `chain.blocks`, `chain.head` e `event_counts` de antes (a bateria não suja o registro real).
- UI (`static/index.html`, `app.js`, `style.css`): botão **"Bateria do artigo"** no cabeçalho do cartão "Painel de ataque" (ao lado de "Restaurar demo"). Ao clicar: mostra em `#attack-result` os contadores animados "14/14 classificações" e "50/50 adulterações rejeitadas" e a `note`. Em verde se 14/14 e 50/50; **em vermelho com os números reais se for diferente** (não force verde). Manter o layout de apresentação sem rolagem em 1366×768.
- `tools/repro_artigo.py` continua passando sem alteração de comportamento (`python tools/repro_artigo.py` imprime os mesmos 3 testes).
- Docs: linha na Seção 10.5; uma frase em `docs/ARTIGO_X_DEMONSTRACAO.md` dizendo que a bateria ao vivo reproduz os testes 1 e 2 (e que o 3, latência, é medido à parte).

**3b. Prova visível quando a corrente quebra.** Ler `src/coldchain/webapp.py` (`chain_verify`) e o trecho de `verifyChain`/`renderChainStatus` em `static/app.js`.
- Estender **`GET /api/chain/verify`** de forma compatível (os 3 campos atuais continuam iguais): quando `motivo` é `hash_quebrado`, acrescentar `hash_gravado` e `hash_recalculado` (hex); quando é `prev_hash_diferente`, `prev_gravado` e `prev_esperado`. Nos casos sem divergência de hash/prev, esses campos **não aparecem**. Para obter os valores, **não altere `Ledger.verify_chain`** (assinatura e retorno atuais são contrato); adicione um método novo em `Ledger` (ex.: `explain_failure(idx)`) coberto por teste em `tests/test_ledger.py`.
- UI: na faixa de estado da corrente (`#chain-status`, estado "bad") e no resultado do ataque "banco adulterado", mostrar em fonte mono, em duas linhas curtas: `gravado     4e57…c91a` / `recalculado 9a1c…02fe` (primeiros 8 e últimos 4 hex). Texto: "O hash gravado não bate com o recalculado a partir do conteúdo atual do bloco."
- Seção 10.5: atualizar a linha de `/api/chain/verify` com os campos opcionais. Teste: `test_webapp.py` (após `corrupt-db`, os campos aparecem e diferem).

**3c. Métricas de cadeia de frio (só no navegador, a partir das leituras exibidas).** Ler a função `renderChartStats` em `app.js`.
- Acrescentar à linha de resumo do gráfico: **excursões** (nº de trechos contíguos fora da faixa segura `low..high`) e **MKT** (temperatura cinética média): `ΔH/R = 10000 K`; `T_K = (ΔH/R) / −ln( (1/n) · Σ exp(−(ΔH/R)/T_i) )`, `T_i` em kelvin, leituras com **peso igual** (diga isso no `title` do rótulo: "MKT das leituras exibidas, pesos iguais"). Resultado em °C com 2 casas.
- Extraia o cálculo para uma função pura exportável (`static/metrics.js`, módulo ES, sem DOM) e teste com `node --test tests/js/metrics.test.mjs`: série constante a 5 °C → MKT 5,00; série alternando 0 e 10 °C → o valor calculado pela fórmula acima no próprio teste (calcule independente, tolerância 1e-9); série vazia → `null`; excursões: `[5,9,9,5,1,5]` → 2.
- Em alturas ≤ 720 px a linha já é escondida pelo CSS existente; não mude isso.

**Aceite (Parte 3):** `python -m unittest` OK (≥ 61 + novos); `node --test tests/js/` OK; Playwright (DOM): clicar "Bateria do artigo" → `#attack-result` contém "14/14" e "50/50"; verificar corrente após `corrupt-db` mostra "gravado" e "recalculado"; zero `pageerror`; `python tools/repro_artigo.py` OK.

## Parte 4 (opcional: só se as Partes 1 a 3 estiverem completas e verdes)

Página `GET /laudo` (imprimível): `static/laudo.html` + `laudo.js`. Busca `/api/export/chain` e `/api/readings?limit=2000`; mostra período, nº de leituras, mín/máx/média, excursões, MKT (usando `metrics.js`), hash da cabeça da corrente, impressão digital (SHA-256, 16 primeiros hex) de cada chave pública, e um QR (`vendor/qrcode.js`) para `<origem>/verificador`. Cabeçalho honesto: "Gerado pelo gateway em <data/hora>. No modo simulado, os valores são simulados." (ler `/api/status` → `simulate`). `@media print` limpo em A4, sem botões. Link "Laudo" no topo. Teste: rota 200 e Playwright `page.pdf()` gera arquivo > 0 B sem `pageerror`. **Se o tempo/custo estiver apertado, pule.**

## Entrega (fim da tarefa)

1. `PYTHONPATH=src python -m unittest discover -s tests` e `node --test tests/js/` verdes; `python tools/repro_artigo.py` OK.
2. `git push -u origin claude/eager-tesla-re5iv3` (**somente esta branch**, nunca outra; sem PR).
3. **Relatório final em até 40 linhas:** para cada parte: `FEITA | PARCIAL | BLOQUEADA`, hash do commit; testes antes → depois (61 → N); arquivos criados/alterados; **o que não foi verificado** (compilação do firmware; ver CI); desvios do que está aqui e por quê; **o que o usuário precisa fazer na sexta** (comandos exatos da Parte 1); qualquer pino ou fato de hardware que você suspeita estar errado em `pins.h` (só anotar).

---

## Procedimento do Claude principal (disparo e revisão)

**Disparo** (só com a frase **COMEÇAR MAXIMIZAÇÃO**, em qualquer caixa):
1. `bash tools/fable_preflight.sh`; se houver FALHA, corrija e rode de novo; se a branch local diferir do remoto, `git push`.
2. `Agent` com `model: "fable"`, `subagent_type: "general-purpose"`, em segundo plano, **sem worktree** (um único agente, direto na branch `claude/eager-tesla-re5iv3`, sem conflito), com o prompt: *"Leia /home/user/softwareMNR/docs/FABLE_TAREFA.md inteiro e execute as Partes 1, 2 e 3 em ordem (Parte 4 só se tudo estiver verde), obedecendo as Regras de custo e a seção Entrega. Responda com o relatório final."*
3. Avisar o usuário que começou e **não** trabalhar nos mesmos arquivos enquanto o Fable roda.

**Revisão** (quando o Fable terminar):
1. `git pull` da branch; `git log --oneline` e `git diff --stat 7fa472a..HEAD`.
2. Rodar `bash tools/fable_preflight.sh`, `node --test tests/js/`, `python tools/repro_artigo.py`.
3. Conferir o CI do GitHub (`mcp__github__actions_list`/`get_job_logs`), **principalmente os jobs `Firmware bench`**; corrigir falhas de compilação do firmware.
4. Revisão visual: subir a tela, capturas (1366×768 e celular) da tela principal, `/verificador`, resultado da bateria e corrente quebrada com os hashes; corrigir o que estiver feio ou cortado.
5. Conferir o princípio de honestidade (nada afirmado que não foi medido; simulado rotulado).
6. Entregar ao usuário: o que ficou pronto, o que depende do CI, e o **roteiro de sexta** da Parte 1.
