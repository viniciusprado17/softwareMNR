#!/usr/bin/env bash
# Pre-checagem ANTES de delegar a "Maximizacao" ao Fable (docs/FABLE_TAREFA.md).
# Falhar aqui e barato; descobrir no meio da tarefa e caro. Uso: bash tools/fable_preflight.sh
cd "$(dirname "$0")/.." || exit 1
FAIL=0
ok()   { echo "OK     $*"; }
warn() { echo "AVISO  $*"; }
fail() { echo "FALHA  $*"; FAIL=1; }

BRANCH_EXPECTED="claude/eager-tesla-re5iv3"
[ "$(git branch --show-current)" = "$BRANCH_EXPECTED" ] && ok "branch $BRANCH_EXPECTED" \
  || fail "branch atual: $(git branch --show-current) (esperado $BRANCH_EXPECTED)"
[ -z "$(git status --porcelain)" ] && ok "arvore de trabalho limpa" || fail "ha alteracoes nao commitadas"
git fetch -q origin "$BRANCH_EXPECTED" 2>/dev/null
if [ "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$BRANCH_EXPECTED" 2>/dev/null)" ]; then
  ok "branch igual ao remoto"
else
  warn "branch local difere do remoto (faca push antes de delegar)"
fi

PY=python3
for c in .venv/bin/python /tmp/claude-0/venv/bin/python; do [ -x "$c" ] && PY="$c" && break; done
if "$PY" -c "import fastapi, uvicorn, cryptography, httpx" 2>/dev/null; then
  ok "dependencias Python ($PY)"
else
  fail "faltam dependencias: $PY -m pip install -r requirements.txt httpx"
fi
OUT=$(PYTHONPATH=src "$PY" -m unittest discover -s tests 2>&1 | tail -3)
echo "$OUT" | grep -q "^OK$" && ok "testes: $(echo "$OUT" | grep '^Ran')" || { fail "testes Python"; echo "$OUT"; }

if command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 20 ]; then
  ok "node $(node --version)"
  node -e '
    const v=require("./tests/vectors.json"), hex=h=>Uint8Array.from(h.match(/../g).map(b=>parseInt(b,16)));
    (async()=>{const k=await crypto.subtle.importKey("raw",hex(v.public_key_hex),{name:"ECDSA",namedCurve:"P-256"},false,["verify"]);
      for(const x of v.vectors){const r=await crypto.subtle.verify({name:"ECDSA",hash:"SHA-256"},k,hex(x.sig_hex),hex(x.payload_hex));
        if(r!==(x.expect==="valid")){console.log("divergiu no vetor");process.exit(1)}}})()' \
    && ok "WebCrypto confere os 6 vetores (4 validos, 2 invalidos de proposito)" \
    || fail "WebCrypto nao bateu com tests/vectors.json"
else
  fail "node >= 20 ausente (o verificador no navegador precisa de WebCrypto no teste)"
fi
NODE_PATH=$(npm root -g 2>/dev/null) node -e 'require("playwright")' 2>/dev/null \
  && ok "playwright disponivel (NODE_PATH=\$(npm root -g))" || warn "playwright ausente: testes de pagina ficam so no DOM via node"

if curl -sS -m 8 -o /dev/null https://registry.platformio.org 2>/dev/null; then
  ok "registro do PlatformIO acessivel: da para compilar o firmware aqui"
else
  warn "registro do PlatformIO INACESSIVEL: firmware nao compila nesta maquina; a prova e o CI do GitHub"
fi
[ "$FAIL" = 0 ] && echo "=> pronto para COMECAR MAXIMIZACAO" || echo "=> corrija as FALHAS antes de delegar"
exit "$FAIL"
