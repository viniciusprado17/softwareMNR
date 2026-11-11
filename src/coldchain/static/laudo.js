// Laudo imprimivel: resumo das leituras + conferencia da corrente no navegador.
import { countExcursions, meanKineticTemp } from "./metrics.js";
import { REASONS, hexToBytes, verifyExport } from "./verifier-core.js";

const $ = (id) => document.getElementById(id);
const num = (n, d = 2) => Number(n).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const when = (ts) => new Date(ts * 1000).toLocaleString("pt-BR");
const facts = (rows) => rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
const short = (h) => `${h.slice(0, 12)}…${h.slice(-6)}`;

try { document.documentElement.dataset.theme = localStorage.getItem("cc-theme") || "dark"; } catch (e) { /* sem storage */ }

async function getJson(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function verifierUrl() {
  const local = ["localhost", "127.0.0.1", "[::1]", "::1"].includes(location.hostname);
  if (local) {
    try {
      const a = await getJson("/api/access");
      if (a.urls.length) return `${a.urls[0]}/verificador`;
    } catch (e) { /* segue com o endereco atual */ }
  }
  return `${location.origin}/verificador`;
}

async function main() {
  const [status, doc, readings] = await Promise.all([
    getJson("/api/status"), getJson("/api/export/chain"), getJson("/api/readings?limit=2000")]);
  const { low, high } = status.thresholds;
  $("l-gen").textContent = `Gerado em ${new Date().toLocaleString("pt-BR")} pelo gateway (${status.simulate ? "modo simulado" : `hardware · ${status.serial.source || "serial"}`}).`;
  $("l-sim").hidden = !status.simulate;
  $("l-range").textContent = `${num(low, 0)} a ${num(high, 0)} °C`;

  const t = readings.map((r) => r.temp_c);
  const out = t.filter((v) => v < low || v > high).length;
  const nodes = [...new Set(readings.map((r) => r.node_id))].join(", ") || "–";
  $("l-period").innerHTML = readings.length ? facts([
    ["Início", when(readings[0].rx_ts)], ["Fim", when(readings[readings.length - 1].rx_ts)],
    ["Leituras", t.length.toLocaleString("pt-BR")], ["Nó(s)", nodes],
  ]) : facts([["Leituras", "nenhuma"]]);
  $("l-temp").innerHTML = t.length ? facts([
    ["Mínima", `${num(Math.min(...t))} °C`], ["Máxima", `${num(Math.max(...t))} °C`],
    ["Média", `${num(t.reduce((a, b) => a + b, 0) / t.length)} °C`], ["MKT", `${num(meanKineticTemp(t))} °C`],
    ["Fora da faixa", `<b class="${out ? "bad-text" : "ok-text"}">${out} de ${t.length}</b>`],
    ["Excursões", `<b class="${out ? "bad-text" : "ok-text"}">${countExcursions(t, low, high)}</b>`],
  ]) : "";

  const res = await verifyExport(doc);
  const fps = await Promise.all(Object.entries(doc.nodes).map(async ([id, k]) => {
    const d = new Uint8Array(await crypto.subtle.digest("SHA-256", hexToBytes(k)));
    return `nó ${id}: <code>${Array.from(d.slice(0, 8), (b) => b.toString(16).padStart(2, "0")).join("")}</code>`;
  }));
  $("l-chain").innerHTML = facts([
    ["Blocos", doc.blocks.length.toLocaleString("pt-BR")], ["Cabeça", `<code>${short(doc.head)}</code>`],
    ["Chave(s)", fps.join("<br>") || "–"], ["Algoritmo", "ECDSA P-256 + SHA-256"],
  ]);
  const v = $("l-verdict");
  v.className = `l-verdict ${res.ok ? "ok" : "bad"}`;
  v.textContent = res.ok ? `CORRENTE ÍNTEGRA · ${doc.blocks.length} blocos conferidos neste navegador`
    : `CORRENTE QUEBRADA no bloco ${res.bad.idx}: ${REASONS[res.bad.reason] || res.bad.reason}`;

  const url = await verifierUrl();
  $("l-url").textContent = url;
  const qr = qrcode(0, "M");
  qr.addData(url);
  qr.make();
  $("l-qr").innerHTML = qr.createSvgTag({ cellSize: 4, margin: 16, scalable: true });
  document.body.dataset.ready = "1";
}

$("btn-print").addEventListener("click", () => window.print());
main().catch((e) => {
  $("l-verdict").className = "l-verdict bad";
  $("l-verdict").textContent = `Não consegui gerar o laudo: ${e.message}`;
  document.body.dataset.ready = "1";
});
