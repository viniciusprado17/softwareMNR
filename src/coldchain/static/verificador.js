// Pagina do verificador independente. A logica de verificacao fica em verifier-core.js
// (testada contra o Python em tests/js/verifier.test.mjs).
import { REASONS, bytesToHex, decodePayload, hexToBytes, verifyExport } from "./verifier-core.js";

const $ = (id) => document.getElementById(id);
const STATUS = ["OK", "ALERTA", "ALARME"];
const MAX_ROWS = 400;
const state = { doc: null, source: "" };

try { document.documentElement.dataset.theme = localStorage.getItem("cc-theme") || "dark"; } catch (e) { /* sem storage */ }

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const short = (h) => (h && h.length > 16 ? `${h.slice(0, 8)}…${h.slice(-4)}` : h || "–");

async function fingerprint(hex) {
  const d = await crypto.subtle.digest("SHA-256", hexToBytes(hex));
  return bytesToHex(new Uint8Array(d)).slice(0, 16);
}

function setVerdict(kind, title, sub) {
  $("verdict-card").className = `card verdict ${kind}`;
  $("v-icon").innerHTML = `<svg><use href="#i-${kind === "ok" ? "shield-check" : kind === "bad" ? "shield-x" : "fingerprint"}"/></svg>`;
  $("verdict").textContent = title;
  $("verdict-sub").textContent = sub;
}

async function renderFacts(doc) {
  const nodes = Object.entries(doc.nodes || {});
  const fps = await Promise.all(nodes.map(async ([id, k]) => `nó ${esc(id)}: <code>${await fingerprint(k)}</code>`));
  const data = doc.blocks.filter((b) => b.kind === "data").length;
  $("facts").innerHTML = `
    <dt>Origem</dt><dd>${esc(state.source)}</dd>
    <dt>Blocos</dt><dd>${doc.blocks.length.toLocaleString("pt-BR")} (${data.toLocaleString("pt-BR")} leituras)</dd>
    <dt>Cabeça</dt><dd><code>${short(doc.head)}</code></dd>
    <dt>Chaves (impressão digital SHA-256)</dt><dd>${fps.join("<br>") || "nenhuma"}</dd>
    <dt>Formato</dt><dd>${esc(doc.format || "?")} · ${esc(doc.curve || "?")}</dd>`;
}

function renderRows(doc, res) {
  const verdicts = new Map(res.blocks.map((b) => [b.idx, b]));
  let blocks = doc.blocks;
  let note = "";
  if (blocks.length > MAX_ROWS) {
    const badPos = res.bad ? blocks.findIndex((b) => b.idx === res.bad.idx) : blocks.length;
    const end = Math.min(blocks.length, Math.max(badPos + 5, MAX_ROWS));
    blocks = blocks.slice(end - MAX_ROWS, end);
    note = `mostrando ${MAX_ROWS} de ${doc.blocks.length.toLocaleString("pt-BR")} blocos`;
  }
  $("list-note").textContent = note;
  $("rows").innerHTML = blocks.slice().reverse().map((b) => {
    const v = verdicts.get(b.idx);
    let reading = b.kind === "resync" ? "ressincronização" : "–";
    try {
      const r = b.kind === "data" ? decodePayload(hexToBytes(b.payload)) : null;
      if (r) reading = `${r.temp_c.toFixed(2).replace(".", ",")} °C · ${STATUS[r.status] || "?"}`;
    } catch (e) { reading = "payload ilegível"; }
    const badge = !v ? '<span class="badge info">não conferido</span>'
      : v.ok ? '<span class="badge ok">✓ confere</span>'
      : `<span class="badge bad">✗ ${esc(REASONS[v.reason] || v.reason)}</span>`;
    return `<tr class="${v && !v.ok ? "bad-row" : ""}"><td>${b.idx}</td><td>${b.node_id} · ${b.seq}</td><td>${reading}</td>` +
      `<td class="mono">${short(b.hash)}</td><td>${badge}</td></tr>`;
  }).join("") || '<tr><td colspan="5" class="t">corrente vazia</td></tr>';
}

async function check(doc, tamperedIdx = null) {
  setVerdict("idle", "Verificando…", "Recalculando hashes e conferindo assinaturas no navegador.");
  const t0 = performance.now();
  let res;
  try { res = await verifyExport(doc); } catch (e) {
    setVerdict("bad", "Arquivo inválido", e.message);
    return;
  }
  const ms = Math.round(performance.now() - t0);
  const n = doc.blocks.length.toLocaleString("pt-BR");
  if (res.ok) {
    setVerdict("ok", `CORRENTE ÍNTEGRA · ${n} blocos`, `Todos os hashes e assinaturas conferem (${ms} ms neste navegador).`);
  } else {
    const why = REASONS[res.bad.reason] || res.bad.reason;
    setVerdict("bad", `QUEBRADA no bloco ${res.bad.idx}: ${why}`,
      tamperedIdx != null ? `A adulteração simulada no bloco ${tamperedIdx} foi detectada. Os blocos seguintes não foram conferidos.`
        : `${res.checked.toLocaleString("pt-BR")} blocos conferidos até a falha. Os seguintes não foram conferidos.`);
  }
  await renderFacts(doc);
  renderRows(doc, res);
}

async function useDoc(doc, source) {
  state.doc = doc;
  state.source = source;
  $("btn-tamper").disabled = !doc.blocks.some((b) => b.kind === "data");
  $("tamper-note").hidden = true;
  await check(doc);
}

$("btn-load").addEventListener("click", async () => {
  try {
    const res = await fetch("/api/export/chain");
    if (!res.ok) throw new Error(`gateway respondeu ${res.status}`);
    await useDoc(await res.json(), "gateway (ao vivo)");
  } catch (e) { setVerdict("bad", "Não consegui carregar do gateway", e.message); }
});

$("file-in").addEventListener("change", async (ev) => {
  const f = ev.target.files[0];
  if (!f) return;
  try { await useDoc(JSON.parse(await f.text()), `arquivo ${f.name}`); } catch (e) { setVerdict("bad", "Arquivo inválido", e.message); }
  ev.target.value = "";
});

// Inverte 1 bit da temperatura de um bloco no MEIO da corrente, so na memoria desta pagina.
$("btn-tamper").addEventListener("click", async () => {
  const doc = structuredClone(state.doc);
  const data = doc.blocks.filter((b) => b.kind === "data");
  const target = data[Math.floor((data.length - 1) / 2)];
  const p = hexToBytes(target.payload);
  p[12] ^= 1;
  target.payload = bytesToHex(p);
  $("tamper-note").hidden = false;
  $("tamper-note").textContent = `Simulação: 1 bit da temperatura do bloco ${target.idx} foi invertido na memória desta página. O gateway não foi alterado; recarregue para voltar ao original.`;
  await check(doc, target.idx);
});
