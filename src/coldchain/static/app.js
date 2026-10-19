// Tela de demonstracao: consulta a API a cada 1 s (sem WebSocket, sem CDN).
"use strict";

const $ = (id) => document.getElementById(id);
const STATUS = { 0: "OK", 1: "ALERTA", 2: "ALARME" };
const BAD = new Set(["assinatura_invalida", "replay", "no_desconhecido", "tamanho_invalido",
  "payload_invalido", "silencio", "demo_banco_adulterado"]);
let thresholds = { low: 2, high: 8 };
let badBlock = null;

async function api(path, opts) {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

const fmtTime = (ts) => ts ? new Date(ts * 1000).toLocaleTimeString("pt-BR") : "-";

function renderStatus(s) {
  const conn = $("conn");
  conn.classList.toggle("on", s.serial.connected);
  $("conn-text").textContent = s.serial.connected
    ? `${s.simulate ? "simulado" : "serial " + s.serial.source} · ${s.serial.rx} pacotes`
    : "receptor desconectado";
  $("blocks").textContent = s.chain.blocks;
  $("head").textContent = s.chain.head.slice(0, 12);
  thresholds = s.thresholds;
  $("range").textContent = `${thresholds.low}–${thresholds.high}`;
  $("attack").hidden = !s.demo_controls;
  $("sim-box").hidden = !s.simulate;
  $("btn-heat").textContent = s.heating ? "Parar aquecimento" : "Simular aquecimento";
  $("btn-heat").dataset.on = s.heating ? "1" : "0";
  const node = s.nodes[0];
  if (node) {
    $("node-id").textContent = node.node_id;
    $("age").textContent = node.seconds_since_last == null ? "-" : `${node.seconds_since_last} s atrás`;
    if (node.silent) {
      const pill = $("status");
      pill.className = "status-pill silent";
      pill.textContent = "SILÊNCIO";
    }
  }
  return node;
}

function renderNode(last, node) {
  if (!last) return;
  $("temp").textContent = last.temp_c.toFixed(2);
  $("hum").textContent = `${last.hum_pct.toFixed(1)} %`;
  $("seq").textContent = last.seq;
  $("radio").textContent = last.rssi == null ? "-" : `${last.rssi} dBm / ${last.snr} dB`;
  if (!node || !node.silent) {
    const pill = $("status");
    pill.className = `status-pill s${last.status}`;
    pill.textContent = STATUS[last.status] + (last.anomaly ? " (anomalia)" : "");
  }
}

function drawChart(readings) {
  const c = $("chart");
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth, h = c.clientHeight;
  c.width = w * dpr; c.height = h * dpr;
  const g = c.getContext("2d");
  g.scale(dpr, dpr);
  g.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.documentElement);
  const pad = { l: 40, r: 10, t: 10, b: 22 };
  const temps = readings.map((r) => r.temp_c);
  const lo = Math.min(thresholds.low - 1, ...temps), hi = Math.max(thresholds.high + 1, ...temps);
  const y = (t) => pad.t + (hi - t) / (hi - lo) * (h - pad.t - pad.b);
  const x = (i) => pad.l + (readings.length < 2 ? 0 : i / (readings.length - 1)) * (w - pad.l - pad.r);
  // faixa segura
  g.fillStyle = css.getPropertyValue("--band");
  g.fillRect(pad.l, y(thresholds.high), w - pad.l - pad.r, y(thresholds.low) - y(thresholds.high));
  // eixos e grade
  g.strokeStyle = css.getPropertyValue("--line");
  g.fillStyle = css.getPropertyValue("--muted");
  g.font = "12px system-ui";
  g.lineWidth = 1;
  const step = (hi - lo) > 12 ? 4 : 2;
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) {
    g.beginPath(); g.moveTo(pad.l, y(t)); g.lineTo(w - pad.r, y(t)); g.stroke();
    g.fillText(`${t}°`, 6, y(t) + 4);
  }
  if (readings.length) {
    g.fillText(fmtTime(readings[0].rx_ts), pad.l, h - 6);
    const lastLabel = fmtTime(readings[readings.length - 1].rx_ts);
    g.fillText(lastLabel, w - pad.r - g.measureText(lastLabel).width, h - 6);
  }
  // serie
  g.strokeStyle = css.getPropertyValue("--accent");
  g.lineWidth = 2;
  g.beginPath();
  readings.forEach((r, i) => (i ? g.lineTo(x(i), y(r.temp_c)) : g.moveTo(x(i), y(r.temp_c))));
  g.stroke();
  readings.forEach((r, i) => {
    g.fillStyle = css.getPropertyValue(r.status === 2 ? "--alarm" : r.status === 1 ? "--warn" : "--ok");
    g.beginPath(); g.arc(x(i), y(r.temp_c), 3, 0, 2 * Math.PI); g.fill();
    if (r.idx === badBlock) {  // bloco apontado pela verificacao da corrente
      g.strokeStyle = css.getPropertyValue("--alarm");
      g.lineWidth = 3;
      g.beginPath(); g.arc(x(i), y(r.temp_c), 9, 0, 2 * Math.PI); g.stroke();
    }
  });
}

function renderEvents(events) {
  const rows = events.map((e) => {
    const cls = e.kind === "aceito" ? "r-aceito" : BAD.has(e.kind) ? "r-bad" : "r-info";
    return `<tr><td>${fmtTime(e.rx_ts)}</td><td>${e.node_id ?? "-"}</td>` +
      `<td class="${cls}">${e.kind.toUpperCase().replaceAll("_", " ")}</td>` +
      `<td>${escapeHtml(e.detail || "")}</td></tr>`;
  });
  $("events").innerHTML = rows.join("");
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function showResult(el, ok, text) {
  el.className = `verify ${ok ? "ok" : "bad"}`;
  el.textContent = text;
}

async function refresh() {
  try {
    const [s, readings, events] = await Promise.all([
      api("/api/status"), api("/api/readings?limit=120"), api("/api/events?limit=50"),
    ]);
    const node = renderStatus(s);
    renderNode(readings[readings.length - 1], node);
    drawChart(readings);
    renderEvents(events);
  } catch (e) {
    $("conn").classList.remove("on");
    $("conn-text").textContent = "gateway fora do ar";
  }
}

async function verifyChain() {
  const v = await api("/api/chain/verify");
  badBlock = v.ok ? null : v.bloco_invalido;
  showResult($("verify-result"), v.ok,
    v.ok ? "Corrente íntegra: todos os blocos conferem (hash e assinatura)."
      : `Corrente QUEBRADA no bloco ${v.bloco_invalido}: ${v.motivo.replaceAll("_", " ")}`);
}

async function demo(action, btn) {
  btn.disabled = true;
  const el = $("attack-result");
  try {
    const r = await api(`/api/demo/${action}`, { method: "POST" });
    if (action === "tamper") {
      showResult(el, r.result !== "aceito",
        `Pacote adulterado (${r.original_temp.toFixed(2)} → ${r.forged_temp.toFixed(2)} °C): ` +
        r.result.toUpperCase().replaceAll("_", " "));
    } else if (action === "replay") {
      showResult(el, r.result !== "aceito", `Pacote reenviado (seq ${r.seq}): ${r.result.toUpperCase()}`);
    } else if (action === "corrupt-db") {
      showResult(el, false,
        `Bloco ${r.idx} editado direto no banco (${r.from_temp.toFixed(2)} → ${r.to_temp.toFixed(2)} °C). ` +
        "Clique em \"Verificar corrente\".");
    } else {
      badBlock = null;
      $("verify-result").className = "verify";
      showResult(el, true, "Demonstração restaurada.");
    }
  } catch (e) {
    showResult(el, false, `Erro: ${e.message}`);
  } finally {
    btn.disabled = false;
    refresh();
  }
}

$("btn-verify").addEventListener("click", () => verifyChain().then(refresh));
document.querySelectorAll("[data-demo]").forEach((b) =>
  b.addEventListener("click", () => demo(b.dataset.demo, b)));
$("btn-heat").addEventListener("click", async (ev) => {
  const on = ev.target.dataset.on !== "1";
  await api("/api/sim/heat", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ on }),
  });
  refresh();
});
window.addEventListener("resize", refresh);
refresh();
setInterval(refresh, 1000);
