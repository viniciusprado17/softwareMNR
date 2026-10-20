// Tela de demonstracao: consulta a API a cada 1 s (sem WebSocket, sem CDN).
"use strict";

const $ = (id) => document.getElementById(id);
const STATUS = { 0: "OK", 1: "ALERTA", 2: "ALARME" };
const STATUS_ICON = { 0: "circle-check", 1: "triangle-alert", 2: "flame" };
const BAD = new Set(["assinatura_invalida", "replay", "no_desconhecido", "tamanho_invalido",
  "payload_invalido", "silencio", "demo_banco_adulterado"]);
const ATTACK_KINDS = ["assinatura_invalida", "replay", "no_desconhecido", "tamanho_invalido", "payload_invalido"];
const LABELS = {
  aceito: "ACEITO", assinatura_invalida: "ASSINATURA INVÁLIDA", replay: "REPLAY",
  no_desconhecido: "NÓ DESCONHECIDO", tamanho_invalido: "TAMANHO INVÁLIDO", payload_invalido: "PAYLOAD INVÁLIDO",
  silencio: "SILÊNCIO", ressincronizacao: "RESSINCRONIZAÇÃO", demo_banco_adulterado: "BANCO ADULTERADO",
};
const REASONS = {
  hash_quebrado: "hash quebrado", prev_hash_diferente: "elo com o bloco anterior quebrado",
  assinatura_invalida: "assinatura inválida", coluna_divergente: "dados divergentes do payload",
};

const state = {
  thresholds: { low: 2, high: 8 }, badBlock: null, verifiedHead: null, filter: "all",
  lastEventId: 0, lastBlockIdx: 0, readings: [], chart: null,
};

const icon = (name) => `<svg><use href="#i-${name}"/></svg>`;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtTime = (ts) => (ts ? new Date(ts * 1000).toLocaleTimeString("pt-BR") : "–");
const fmtNum = (n, d = 2) => (n == null ? "--" : Number(n).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

async function api(path, opts) {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

// ---------------------------------------------------------------- tema
function loadTheme() {
  let t = "dark";
  try { t = localStorage.getItem("cc-theme") || "dark"; } catch (e) { /* sem storage */ }
  document.documentElement.dataset.theme = t;
}
function toggleTheme() {
  const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("cc-theme", t); } catch (e) { /* sem storage */ }
  if (state.chart) { state.chart.destroy(); state.chart = null; drawChart(state.readings); }
}

// ---------------------------------------------------------------- toasts e resultados
function toast(ok, text) {
  const el = document.createElement("div");
  el.className = `toast ${ok ? "ok" : "bad"}`;
  el.innerHTML = icon(ok ? "shield-check" : "shield-alert") + `<span>${esc(text)}</span>`;
  const box = $("toasts");
  box.appendChild(el);
  while (box.children.length > 3) box.firstElementChild.remove();
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 350); }, 3200);
}
function showResult(el, ok, html) {
  el.hidden = false;
  el.className = `result ${ok ? "ok" : "bad"}`;
  el.innerHTML = icon(ok ? "shield-check" : "shield-x") + `<span>${html}</span>`;
}

// ---------------------------------------------------------------- KPIs
function renderStatus(s) {
  const conn = $("conn");
  conn.classList.toggle("on", s.serial.connected);
  $("conn-text").textContent = s.serial.connected ? `ao vivo · ${s.serial.rx} pacotes` : "receptor desconectado";
  const mode = $("mode-chip");
  mode.className = `chip mode ${s.simulate ? "sim" : "real"}`;
  $("mode-text").textContent = s.simulate ? "modo simulado" : `hardware · ${s.serial.source || "serial"}`;
  $("btn-heat").hidden = !s.simulate;
  $("subtitle").innerHTML = s.simulate
    ? "<b>Modo simulado:</b> um nó virtual gera e assina as leituras · gateway, corrente de hash e verificações são os reais"
    : "LoRa 915 MHz · ECDSA P-256 · registro encadeado por hash · LACOR/UNIT · MNR 2026";
  $("attack").hidden = !s.demo_controls;

  state.thresholds = s.thresholds;
  $("range").textContent = `${fmtNum(s.thresholds.low, 0)}–${fmtNum(s.thresholds.high, 0)} °C`;
  $("blocks").textContent = s.chain.blocks.toLocaleString("pt-BR");
  $("head").textContent = s.chain.head.slice(0, 12);
  if (state.verifiedHead && state.verifiedHead !== s.chain.head) state.verifiedHead = null;

  const counts = s.event_counts || {};
  $("accepted").textContent = (counts.aceito || 0).toLocaleString("pt-BR");
  const blocked = ATTACK_KINDS.reduce((n, k) => n + (counts[k] || 0), 0);
  $("blocked").textContent = blocked.toLocaleString("pt-BR");
  const parts = [["assinatura_invalida", "assinatura"], ["replay", "replay"], ["no_desconhecido", "nó desconhecido"]]
    .filter(([k]) => counts[k]).map(([k, n]) => `${counts[k]} ${n}`);
  $("blocked-detail").textContent = parts.length ? parts.join(" · ") : "nenhum até agora";

  const heat = $("btn-heat");
  heat.classList.toggle("heating", s.heating);
  heat.dataset.on = s.heating ? "1" : "0";
  heat.querySelector("span").textContent = s.heating ? "Parar aquecimento" : "Simular aquecimento";

  const node = s.nodes[0];
  if (node) {
    $("node-id").textContent = node.node_id;
    $("age").textContent = node.seconds_since_last == null ? "–" : `há ${fmtNum(node.seconds_since_last, 1)} s`;
  }
  return node;
}

function renderNode(last, node) {
  const pill = $("status");
  const card = $("kpi-temp");
  if (node && node.silent) {
    pill.className = "status silent";
    pill.innerHTML = icon("clock") + "<span>SILÊNCIO</span>";
    card.className = "kpi kpi-temp";
  }
  if (!last) return;
  $("temp").textContent = fmtNum(last.temp_c);
  $("hum").textContent = fmtNum(last.hum_pct, 1);
  $("seq").textContent = last.seq;
  $("rssi").textContent = last.rssi ?? "--";
  $("snr").textContent = last.snr == null ? "--" : fmtNum(last.snr, 1);
  if (!node || !node.silent) {
    pill.className = `status s${last.status}`;
    pill.innerHTML = icon(STATUS_ICON[last.status]) + `<span>${STATUS[last.status]}${last.anomaly ? " · anomalia" : ""}</span>`;
    card.className = `kpi kpi-temp s${last.status}`;
  }
}

// ---------------------------------------------------------------- grafico (Chart.js)
function statusColor(st) { return cssVar(st === 2 ? "--bad" : st === 1 ? "--warn" : "--ok"); }

function drawChart(readings) {
  state.readings = readings;
  const labels = readings.map((r) => fmtTime(r.rx_ts));
  const data = readings.map((r) => r.temp_c);
  const colors = readings.map((r) => statusColor(r.status));
  const radius = readings.map((r) => (r.idx === state.badBlock ? 7 : 3));
  const borders = readings.map((r, i) => (r.idx === state.badBlock ? cssVar("--bad") : colors[i]));
  const { low, high } = state.thresholds;
  const bad = readings.findIndex((r) => r.idx === state.badBlock);
  const annotations = {
    safe: { type: "box", yMin: low, yMax: high, backgroundColor: cssVar("--band"), borderWidth: 0, drawTime: "beforeDatasetsDraw" },
    hi: { type: "line", yMin: high, yMax: high, borderColor: cssVar("--bad"), borderWidth: 1, borderDash: [5, 5],
      label: { display: true, content: `${high} °C`, position: "end", backgroundColor: "transparent", color: cssVar("--bad"), font: { size: 11, weight: "600" }, yAdjust: -9 } },
    lo: { type: "line", yMin: low, yMax: low, borderColor: cssVar("--warn"), borderWidth: 1, borderDash: [5, 5],
      label: { display: true, content: `${low} °C`, position: "end", backgroundColor: "transparent", color: cssVar("--warn"), font: { size: 11, weight: "600" }, yAdjust: 9 } },
  };
  if (bad >= 0) {
    annotations.badpt = { type: "point", xValue: bad, yValue: data[bad], radius: 11, backgroundColor: "transparent",
      borderColor: cssVar("--bad"), borderWidth: 3 };
  }

  if (!state.chart) {
    const ctx = $("chart").getContext("2d");
    const grad = ctx.createLinearGradient(0, 0, 0, ctx.canvas.clientHeight || 330);
    grad.addColorStop(0, "rgba(59,130,246,.28)");
    grad.addColorStop(1, "rgba(59,130,246,0)");
    state.chart = new Chart(ctx, {
      type: "line",
      data: { labels, datasets: [{ data, borderColor: cssVar("--accent-2"), backgroundColor: grad, fill: true, tension: .32,
        borderWidth: 2.2, pointBackgroundColor: colors, pointBorderColor: borders, pointRadius: radius, pointHoverRadius: 6 }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: { color: cssVar("--faint"), maxTicksLimit: 8, maxRotation: 0 } },
          y: { suggestedMin: low - 1, suggestedMax: high + 1, grid: { color: cssVar("--grid") },
            ticks: { color: cssVar("--faint"), callback: (v) => `${v} °C` } },
        },
        plugins: {
          legend: { display: false },
          annotation: { annotations },
          tooltip: {
            backgroundColor: cssVar("--panel"), titleColor: cssVar("--text"), bodyColor: cssVar("--muted"),
            borderColor: cssVar("--line-2"), borderWidth: 1, padding: 10, displayColors: false,
            callbacks: {
              title: (items) => `seq ${readings[items[0].dataIndex]?.seq ?? ""} · ${items[0].label}`,
              label: (item) => {
                const r = state.readings[item.dataIndex];
                return r ? [`${fmtNum(r.temp_c)} °C · ${STATUS[r.status]}`, `bloco ${r.idx} · ${r.hash.slice(0, 12)}`] : "";
              },
            },
          },
        },
      },
    });
    return;
  }
  const ch = state.chart;
  ch.data.labels = labels;
  const ds = ch.data.datasets[0];
  ds.data = data; ds.pointBackgroundColor = colors; ds.pointBorderColor = borders;
  ds.pointRadius = radius;
  ch.options.plugins.annotation.annotations = annotations;
  ch.options.scales.y.suggestedMin = low - 1;
  ch.options.scales.y.suggestedMax = high + 1;
  ch.update("none");
}

// ---------------------------------------------------------------- corrente
function renderChain(readings, headHash) {
  const last = readings.slice(-8).reverse();
  if (!last.length) { $("chain").innerHTML = '<div class="empty">aguardando o primeiro pacote…</div>'; return; }
  const verified = state.verifiedHead && state.verifiedHead === headHash;
  $("chain").innerHTML = last.map((r) => {
    const cls = (r.idx === state.badBlock ? "broken" : verified ? "verified" : "") +
      (state.lastBlockIdx && r.idx > state.lastBlockIdx ? " new" : "");
    return `<div class="block ${cls}">
      <span class="b-idx">${r.idx}</span>
      <span class="b-main"><b>${fmtNum(r.temp_c)} °C</b> · seq ${r.seq}<span class="mono">${r.hash.slice(0, 24)}…</span></span>
      <span class="b-st s${r.status}">${r.idx === state.badBlock ? "ADULTERADO" : STATUS[r.status]}</span>
    </div>`;
  }).join("");
  state.lastBlockIdx = last[0].idx;
}

// ---------------------------------------------------------------- eventos
function renderEvents(events) {
  const maxId = events.length ? events[0].id : 0;
  const rows = events.filter((e) => state.filter === "all" || (state.filter === "ok" ? e.kind === "aceito" : BAD.has(e.kind)))
    .map((e) => {
      const kind = e.kind === "aceito" ? "ok" : BAD.has(e.kind) ? "bad" : "info";
      const ic = kind === "ok" ? "shield-check" : kind === "bad" ? "shield-alert" : "triangle-alert";
      const fresh = state.lastEventId && e.id > state.lastEventId ? "fresh" : "";
      return `<tr class="${fresh}"><td class="t">${fmtTime(e.rx_ts)}</td><td>${e.node_id ?? "–"}</td>` +
        `<td><span class="badge ${kind}">${icon(ic)}${LABELS[e.kind] || esc(e.kind.toUpperCase())}</span></td>` +
        `<td class="d">${esc(e.detail || "")}</td></tr>`;
    });
  $("events").innerHTML = rows.join("") || '<tr><td colspan="4" class="t">nenhum evento neste filtro</td></tr>';
  state.lastEventId = maxId;
}

// ---------------------------------------------------------------- ciclo
async function refresh() {
  try {
    const [s, readings, events] = await Promise.all([
      api("/api/status"), api("/api/readings?limit=90"), api("/api/events?limit=80"),
    ]);
    const node = renderStatus(s);
    renderNode(readings[readings.length - 1], node);
    drawChart(readings);
    renderChain(readings, s.chain.head);
    renderEvents(events);
  } catch (e) {
    $("conn").classList.remove("on");
    $("conn-text").textContent = "gateway fora do ar";
  }
}

async function verifyChain() {
  const btn = $("btn-verify");
  btn.disabled = true;
  try {
    const v = await api("/api/chain/verify");
    state.badBlock = v.ok ? null : v.bloco_invalido;
    if (v.ok) {
      state.verifiedHead = (await api("/api/status")).chain.head;
      showResult($("verify-result"), true, "Corrente íntegra: hash e assinatura de todos os blocos conferem.");
      toast(true, "Corrente íntegra");
    } else {
      state.verifiedHead = null;
      showResult($("verify-result"), false, `Corrente QUEBRADA no bloco <b>${v.bloco_invalido}</b>: ${REASONS[v.motivo] || v.motivo}.`);
      toast(false, `Fraude detectada no bloco ${v.bloco_invalido}`);
    }
  } finally {
    btn.disabled = false;
    refresh();
  }
}

async function demo(action, btn) {
  btn.disabled = true;
  const el = $("attack-result");
  try {
    const r = await api(`/api/demo/${action}`, { method: "POST" });
    if (action === "tamper") {
      const blocked = r.result !== "aceito";
      showResult(el, blocked, `Pacote adulterado (${fmtNum(r.original_temp)} → ${fmtNum(r.forged_temp)} °C): <b>${LABELS[r.result] || r.result}</b>. O pacote falso não entrou na corrente.`);
      toast(blocked, blocked ? "Adulteração bloqueada: assinatura inválida" : "Pacote adulterado ACEITO");
    } else if (action === "replay") {
      const blocked = r.result !== "aceito";
      showResult(el, blocked, `Pacote reenviado (seq ${r.seq}): <b>${LABELS[r.result] || r.result}</b>. A assinatura é válida, mas o seq já foi usado.`);
      toast(blocked, blocked ? "Replay bloqueado" : "Replay ACEITO");
    } else if (action === "corrupt-db") {
      showResult(el, false, `Bloco <b>${r.idx}</b> editado direto no banco (${fmtNum(r.from_temp)} → ${fmtNum(r.to_temp)} °C). Clique em <b>Verificar corrente</b>.`);
      toast(false, `Banco adulterado no bloco ${r.idx}`);
    } else {
      state.badBlock = null; state.verifiedHead = null;
      $("verify-result").hidden = true;
      el.hidden = true;
      toast(true, "Demonstração restaurada");
    }
  } catch (e) {
    showResult(el, false, `Erro: ${esc(e.message)}`);
  } finally {
    btn.disabled = false;
    refresh();
  }
}

async function downloadCsv() {
  const rows = await api("/api/readings?limit=2000");
  const head = ["bloco", "no", "seq", "hora_recebimento", "temperatura_c", "umidade_pct", "status", "rssi_dbm", "snr_db", "anomalia", "hash"];
  const lines = rows.map((r) => [r.idx, r.node_id, r.seq, new Date(r.rx_ts * 1000).toISOString(), r.temp_c, r.hum_pct,
    STATUS[r.status], r.rssi ?? "", r.snr ?? "", r.anomaly ?? "", r.hash].join(";"));
  const blob = new Blob(["﻿" + [head.join(";"), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `leituras_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---------------------------------------------------------------- eventos de interface
loadTheme();
$("theme-btn").addEventListener("click", toggleTheme);
$("fs-btn").addEventListener("click", () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => toast(false, "Tela cheia indisponível: use F11"));
});
document.addEventListener("fullscreenchange", () => document.documentElement.classList.toggle("is-full", !!document.fullscreenElement));
$("btn-verify").addEventListener("click", verifyChain);
$("btn-csv").addEventListener("click", () => downloadCsv().catch((e) => toast(false, e.message)));
document.querySelectorAll("[data-demo]").forEach((b) => b.addEventListener("click", () => demo(b.dataset.demo, b)));
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
  state.filter = t.dataset.filter;
  refresh();
}));
$("btn-heat").addEventListener("click", async (ev) => {
  const on = ev.currentTarget.dataset.on !== "1";
  await api("/api/sim/heat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ on }) });
  refresh();
});
setInterval(() => { $("clock").textContent = new Date().toLocaleTimeString("pt-BR"); }, 1000);
$("clock").textContent = new Date().toLocaleTimeString("pt-BR");
refresh();
setInterval(refresh, 1000);
