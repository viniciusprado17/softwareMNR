// Tela de demonstracao: consulta a API a cada 1 s (sem WebSocket, sem CDN).
"use strict";

import { countExcursions, meanKineticTemp } from "./metrics.js";

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
  thresholds: { low: 2, high: 8 }, badBlock: null, badReason: null, badProof: null, verified: null, filter: "all",
  lastEventId: 0, lastBlockIdx: 0, readings: [], chart: null, prevBlocked: null,
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
  $("conn-text").innerHTML = s.serial.connected
    ? `ao vivo<span class="more"> · ${s.serial.rx} pacotes</span>` : "receptor desconectado";
  const mode = $("mode-chip");
  mode.className = `chip mode ${s.simulate ? "sim" : "real"}`;
  $("mode-text").textContent = s.simulate ? "modo simulado" : `hardware · ${s.serial.source || "serial"}`;
  $("btn-heat").hidden = !s.simulate;
  $("pipe").classList.toggle("simulated", !!s.simulate);
  $("subtitle").innerHTML = s.simulate
    ? "<b>Modo simulado:</b> um nó virtual gera e assina as leituras · gateway, corrente de hash e verificações são os reais"
    : "LoRa 915 MHz · ECDSA P-256 · registro encadeado por hash · LACOR/UNIT · MNR 2026";
  $("attack").hidden = !s.demo_controls;

  state.thresholds = s.thresholds;
  $("range").textContent = `${fmtNum(s.thresholds.low, 0)}–${fmtNum(s.thresholds.high, 0)} °C`;
  $("blocks").textContent = s.chain.blocks.toLocaleString("pt-BR");
  $("head").textContent = s.chain.head.slice(0, 12);

  const counts = s.event_counts || {};
  $("accepted").textContent = (counts.aceito || 0).toLocaleString("pt-BR");
  const blocked = ATTACK_KINDS.reduce((n, k) => n + (counts[k] || 0), 0);
  $("blocked").textContent = blocked.toLocaleString("pt-BR");
  $("blocked-val").classList.toggle("bad-text", blocked > 0);
  if (state.prevBlocked != null && blocked > state.prevBlocked) {
    const card = $("kpi-blocked");
    card.classList.remove("flash-bad");
    void card.offsetWidth; // reinicia a animacao
    card.classList.add("flash-bad");
  }
  state.prevBlocked = blocked;
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

// Medidor circular de 270 graus: de (faixa baixa - 4) a (faixa alta + 6), com a faixa segura destacada.
const GAUGE = { cx: 60, cy: 60, r: 48, a0: 135, sweep: 270 };
function gaugePoint(deg) {
  const t = (deg * Math.PI) / 180;
  return [GAUGE.cx + GAUGE.r * Math.cos(t), GAUGE.cy + GAUGE.r * Math.sin(t)];
}
function gaugeArc(d0, d1) {
  const [x0, y0] = gaugePoint(d0), [x1, y1] = gaugePoint(d1);
  return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${GAUGE.r} ${GAUGE.r} 0 ${d1 - d0 > 180 ? 1 : 0} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}
function renderGauge(temp) {
  const { low, high } = state.thresholds;
  const min = low - 4, max = high + 6;
  const deg = (v) => GAUGE.a0 + GAUGE.sweep * Math.min(1, Math.max(0, (v - min) / (max - min)));
  $("g-track").setAttribute("d", gaugeArc(GAUGE.a0, GAUGE.a0 + GAUGE.sweep));
  $("g-safe").setAttribute("d", gaugeArc(deg(low), deg(high)));
  if (temp == null) { $("g-val").setAttribute("d", ""); return; }
  const end = deg(temp);
  $("g-val").setAttribute("d", end - GAUGE.a0 < 1 ? "" : gaugeArc(GAUGE.a0, end));
  const [x, y] = gaugePoint(end);
  $("g-dot").setAttribute("cx", x.toFixed(2));
  $("g-dot").setAttribute("cy", y.toFixed(2));
}

function setAlarmLook(last, node) {
  const alarm = !!last && last.status === 2 && !(node && node.silent);
  document.body.classList.toggle("alarm", alarm);
  document.title = alarm ? `ALARME ${fmtNum(last.temp_c)} °C · Cadeia de Frio` : "Cadeia de Frio Segura · MNR 2026";
}

function renderNode(last, node) {
  const pill = $("status");
  const card = $("kpi-temp");
  renderGauge(last ? last.temp_c : null);
  setAlarmLook(last, node);
  $("pipe").querySelector('[data-stage="node"]').classList.toggle("silent", !!(node && node.silent));
  $("pipe").querySelector('[data-stage="sensor"]').classList.toggle("silent", !!(node && node.silent));
  if (node && node.silent) {
    pill.className = "status silent";
    pill.innerHTML = icon("clock") + "<span>SILÊNCIO</span>";
    card.className = "kpi kpi-temp hero";
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
    card.className = `kpi kpi-temp hero s${last.status}`;
  }
}

// ---------------------------------------------------------------- grafico (Chart.js)
function statusColor(st) { return cssVar(st === 2 ? "--bad" : st === 1 ? "--warn" : "--ok"); }

function renderChartStats(readings) {
  const { low, high } = state.thresholds;
  if (!readings.length) { ["min", "max", "avg", "out", "exc", "mkt"].forEach((k) => { $(`st-${k}`).textContent = "--"; }); return; }
  const t = readings.map((r) => r.temp_c);
  const out = t.filter((v) => v < low || v > high).length;
  $("st-min").textContent = `${fmtNum(Math.min(...t))} °C`;
  $("st-max").textContent = `${fmtNum(Math.max(...t))} °C`;
  $("st-avg").textContent = `${fmtNum(t.reduce((a, b) => a + b, 0) / t.length)} °C`;
  $("st-out").textContent = `${out} de ${t.length}`;
  $("st-out").className = out ? "bad-text" : "";
  const exc = countExcursions(t, low, high);
  $("st-exc").textContent = String(exc);
  $("st-exc").className = exc ? "bad-text" : "";
  $("st-mkt").textContent = `${fmtNum(meanKineticTemp(t))} °C`;
}

function drawChart(readings) {
  state.readings = readings;
  renderChartStats(readings);
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
      label: { display: true, content: `${high} °C`, position: "start", backgroundColor: "transparent", color: cssVar("--bad"), font: { size: 11, weight: "600" }, yAdjust: -9 } },
    lo: { type: "line", yMin: low, yMax: low, borderColor: cssVar("--warn"), borderWidth: 1, borderDash: [5, 5],
      label: { display: true, content: `${low} °C`, position: "start", backgroundColor: "transparent", color: cssVar("--warn"), font: { size: 11, weight: "600" }, yAdjust: 9 } },
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

// Contador animado (bateria do artigo). Sem animacao se o usuario pediu movimento reduzido.
function countUp(el, to, ms = 900) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = to; return; }
  const t0 = performance.now();
  const step = (now) => {
    const k = Math.min(1, (now - t0) / ms);
    el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3)));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// Prova da quebra: hash gravado x hash recalculado do conteudo atual (ou elo gravado x esperado).
const cut = (h) => `${h.slice(0, 8)}…${h.slice(-4)}`;
function proofHtml(p) {
  if (!p) return "";
  return `<span class="proof mono" title="O hash gravado não bate com o recalculado a partir do conteúdo atual do bloco."><span>${p[0].padEnd(11, "\u00a0")} ${cut(p[1])}</span>` +
    `<span>${p[2].padEnd(11, "\u00a0")} ${cut(p[3])}</span></span>`;
}

// ---------------------------------------------------------------- corrente
function renderChainStatus(chain) {
  const el = $("chain-status");
  const v = state.verified;
  let kind, ic, html;
  if (state.badBlock != null) {
    kind = "bad"; ic = "shield-x";
    html = `<b>Corrente QUEBRADA</b> no bloco <b>${state.badBlock}</b>: ${REASONS[state.badReason] || esc(state.badReason || "")}` +
      proofHtml(state.badProof);
  } else if (v && v.head === chain.head) {
    kind = "ok"; ic = "shield-check";
    html = `<b>Corrente íntegra</b> · ${v.blocks.toLocaleString("pt-BR")} ${v.blocks === 1 ? "bloco verificado" : "blocos verificados"} às ${fmtTime(v.ts)}`;
  } else if (v) {
    const fresh = Math.max(0, chain.blocks - v.blocks);
    kind = "stale"; ic = "clock";
    html = `Íntegra até o bloco ${v.blocks} · <b>${fresh}</b> ${fresh === 1 ? "bloco novo" : "blocos novos"} sem verificar`;
  } else {
    kind = "idle"; ic = "fingerprint";
    html = "Ainda não verificada: clique em <b>Verificar corrente</b>";
  }
  el.className = `chain-status ${kind}`;
  el.innerHTML = icon(ic) + `<span>${html}</span>`;
}

function renderChain(readings, headHash) {
  const last = readings.slice(-8).reverse();
  if (!last.length) { $("chain").innerHTML = '<div class="empty">aguardando o primeiro pacote…</div>'; return; }
  const verified = state.verified && state.verified.head === headHash;
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

// ---------------------------------------------------------------- trilha do pacote
// Acende as etapas a cada pacote novo. Aceito: ate o registro. Rejeitado: para no gateway,
// que mostra o motivo, e o registro fica marcado "nao gravado". Tudo vem dos eventos reais.
const pipeTimers = {};
function pipeNote(id, text, restore, ms) {
  $(id).textContent = text;
  clearTimeout(pipeTimers[id]);
  pipeTimers[id] = setTimeout(() => { $(id).textContent = restore; }, ms);
}
let pipeHoldUntil = 0; // rejeicao tem prioridade: o proximo pacote aceito nao apaga o aviso
function pipeFire(ev) {
  const pipe = $("pipe");
  if (ev.kind === "aceito" && Date.now() < pipeHoldUntil) return;
  if (ev.kind !== "aceito") pipeHoldUntil = Date.now() + 4000;
  pipe.classList.remove("go-ok", "go-bad", "go-db");
  void pipe.offsetWidth; // reinicia a animacao
  if (ev.kind === "aceito") {
    pipe.classList.add("go-ok");
    pipeNote("gw-note", "assinatura e seq conferem", "confere assinatura e seq", 2600);
    const blk = /bloco=(\d+)/.exec(ev.detail || "");
    pipeNote("ledger-note", blk ? `bloco ${blk[1]} gravado` : "gravado", "cadeia de hash", 2600);
  } else if (ev.kind === "demo_banco_adulterado") {
    pipe.classList.add("go-db");
    pipeNote("ledger-note", "BANCO ALTERADO", "cadeia de hash", 4000);
  } else if (BAD.has(ev.kind)) {
    pipe.classList.add("go-bad");
    pipeNote("gw-note", LABELS[ev.kind] || ev.kind, "confere assinatura e seq", 4000);
    pipeNote("ledger-note", "não gravado", "cadeia de hash", 4000);
  }
  if (BAD.has(ev.kind) && window.matchMedia("(max-width: 760px)").matches) {
    toast(false, LABELS[ev.kind] || ev.kind); // no celular o painel de ataque fica longe
  }
}

// ---------------------------------------------------------------- eventos
function renderEvents(events) {
  const maxId = events.length ? events[0].id : 0;
  if (state.lastEventId) {
    const news = events.filter((e) => e.id > state.lastEventId);
    const worst = news.find((e) => BAD.has(e.kind)) || news.find((e) => e.kind === "aceito");
    if (worst) pipeFire(worst);
  }
  const rows = events.filter((e) => state.filter === "all" || (state.filter === "ok" ? e.kind === "aceito" : BAD.has(e.kind)))
    .map((e) => {
      const kind = e.kind === "aceito" ? "ok" : BAD.has(e.kind) ? "bad" : "info";
      const ic = kind === "ok" ? "shield-check" : kind === "bad" ? "shield-alert" : "triangle-alert";
      const fresh = state.lastEventId && e.id > state.lastEventId ? "fresh" : "";
      const det = esc(e.detail || "");
      return `<tr class="${fresh} ${kind === "bad" ? "bad-row" : ""}"><td class="t">${fmtTime(e.rx_ts)}</td><td>${e.node_id ?? "–"}</td>` +
        `<td><span class="badge ${kind}">${icon(ic)}${LABELS[e.kind] || esc(e.kind.toUpperCase())}</span></td>` +
        `<td class="d" title="${det}">${det}</td></tr>`;
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
    document.body.classList.remove("offline");
    const node = renderStatus(s);
    renderNode(readings[readings.length - 1], node);
    drawChart(readings);
    renderChain(readings, s.chain.head);
    renderChainStatus(s.chain);
    renderEvents(events);
  } catch (e) {
    $("conn").classList.remove("on");
    $("conn-text").textContent = "gateway fora do ar";
    document.body.classList.add("offline");
  }
}

async function verifyChain() {
  const btn = $("btn-verify");
  btn.disabled = true;
  try {
    // o estado e lido antes: um bloco que chegue durante a verificacao aparece como "novo, sem verificar"
    const before = (await api("/api/status")).chain;
    const v = await api("/api/chain/verify");
    state.badBlock = v.ok ? null : v.bloco_invalido;
    state.badReason = v.ok ? null : v.motivo;
    state.badProof = v.hash_gravado ? ["gravado", v.hash_gravado, "recalculado", v.hash_recalculado]
      : v.prev_gravado ? ["elo gravado", v.prev_gravado, "esperado", v.prev_esperado] : null;
    state.verified = v.ok ? { head: before.head, blocks: before.blocks, ts: Date.now() / 1000 } : null;
  } catch (e) {
    toast(false, `Falha ao verificar: ${e.message}`);
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
    } else if (action === "replay") {
      const blocked = r.result !== "aceito";
      showResult(el, blocked, `Pacote reenviado (seq ${r.seq}): <b>${LABELS[r.result] || r.result}</b>. A assinatura é válida, mas o seq já foi usado.`);
    } else if (action === "battery") {
      const c = r.classification, t = r.tamper;
      const ok = c.correct === c.total && t.rejected === t.total && t.genuine_accepted === t.genuine_total;
      showResult(el, ok, `<span class="battery"><span><b class="count" data-to="${c.correct}">0</b>/${c.total} classificações</span>` +
        `<span><b class="count" data-to="${t.rejected}">0</b>/${t.total} adulterações rejeitadas</span>` +
        `<span class="b-ctrl">controle: ${t.genuine_accepted}/${t.genuine_total} originais aceitos</span></span>` +
        `<small class="b-note">${esc(r.note)}</small>`);
      el.querySelectorAll(".count").forEach((n) => countUp(n, Number(n.dataset.to)));
    } else if (action === "corrupt-db") {
      showResult(el, false, `Bloco <b>${r.idx}</b> editado direto no banco (${fmtNum(r.from_temp)} → ${fmtNum(r.to_temp)} °C). Clique em <b>Verificar corrente</b>.`);
    } else {
      state.badBlock = null; state.badReason = null; state.badProof = null; state.verified = null;
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

// ---------------------------------------------------------------- QR code (abrir no celular)
const QR = { tab: "app", urls: {} };
const isLocalHost = () => ["localhost", "127.0.0.1", "[::1]", "::1"].includes(location.hostname);

async function resolveAppAccess() {
  if (!isLocalHost()) {
    return { url: location.origin, note: "Este é o endereço que você já está usando. O celular precisa conseguir alcançá-lo (mesma rede Wi-Fi, ou internet se for o link público)." };
  }
  try {
    const a = await api("/api/access");
    if (a.urls.length) {
      return { url: a.urls[0], others: a.urls.slice(1),
        note: "Celular e computador precisam estar na mesma rede Wi-Fi. Se não abrir, libere o firewall do Windows para Redes privadas." + (a.password_required ? " A tela pede senha." : "") };
    }
    return { url: null, note: "A tela está aberta só neste computador. Para o celular conseguir abrir, reinicie com --host 0.0.0.0 (ex.: run_gateway.bat --simulate --demo-controls --host 0.0.0.0) e clique aqui de novo." };
  } catch (e) {
    return { url: null, note: `Não foi possível descobrir o endereço: ${e.message}` };
  }
}

async function renderQr() {
  const box = $("qr-box"), link = $("qr-url"), note = $("qr-note"), copy = $("qr-copy");
  document.querySelectorAll("#qr-dialog .tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.qr === QR.tab);
    t.setAttribute("aria-selected", t.dataset.qr === QR.tab ? "true" : "false");
  });
  let info;
  if (QR.tab === "3d") {
    info = { url: $("btn-3d").href, note: "Simulação ilustrativa da montagem em 3D (os valores são simulados). Precisa de internet no celular." };
  } else {
    box.textContent = "…";
    info = await resolveAppAccess();
  }
  QR.urls[QR.tab] = info.url;
  note.textContent = info.note + (info.others && info.others.length ? ` Outros endereços deste computador: ${info.others.join(", ")}.` : "");
  copy.hidden = !info.url;
  link.hidden = !info.url;
  if (!info.url) { box.innerHTML = `<div class="qr-off">${icon("smartphone")}<span>QR indisponível</span></div>`; return; }
  const qr = qrcode(0, "M");
  qr.addData(info.url);
  qr.make();
  box.innerHTML = qr.createSvgTag({ cellSize: 4, margin: 16, scalable: true, // 16 = 4 modulos de zona silenciosa (norma)
     title: `QR code: ${info.url}` });
  link.textContent = info.url;
  link.href = info.url;
}

function openQr() {
  const dlg = $("qr-dialog");
  QR.tab = "app";
  if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
  renderQr();
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
$("btn-qr").addEventListener("click", openQr);
$("qr-close").addEventListener("click", () => $("qr-dialog").close());
$("qr-dialog").addEventListener("click", (ev) => { if (ev.target === ev.currentTarget) ev.currentTarget.close(); });
document.querySelectorAll("#qr-dialog .tab").forEach((t) => t.addEventListener("click", () => { QR.tab = t.dataset.qr; renderQr(); }));
$("qr-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(QR.urls[QR.tab] || ""); toast(true, "Link copiado"); }
  catch (e) { toast(false, "Não consegui copiar: selecione o link e copie à mão"); }
});
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => { /* sem HTTPS/localhost: segue sem app instalavel */ });
$("btn-csv").addEventListener("click", () => downloadCsv().catch((e) => toast(false, e.message)));
document.querySelectorAll("[data-demo]").forEach((b) => b.addEventListener("click", () => demo(b.dataset.demo, b)));
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((x) => {
    x.classList.toggle("active", x === t);
    x.setAttribute("aria-selected", x === t ? "true" : "false");
  });
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
