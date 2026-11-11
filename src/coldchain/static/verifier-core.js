// Verificador independente da corrente (sem DOM: roda no navegador e no Node >= 20).
// Reproduz Ledger.verify_chain do gateway (mesma ordem, mesmos motivos), usando so o
// documento exportado em GET /api/export/chain e o WebCrypto (ECDSA P-256 + SHA-256).
// Nao adicionar verificacoes que o Python nao faz: tests/js/verifier.test.mjs cobra paridade.

export const REASONS = {
  prev_hash_diferente: "elo com o bloco anterior quebrado",
  hash_quebrado: "hash não bate com o conteúdo do bloco",
  assinatura_invalida: "assinatura inválida",
  coluna_divergente: "dados do bloco divergentes",
};

export function hexToBytes(hex) {
  if (typeof hex !== "string" || hex.length % 2 || /[^0-9a-f]/i.test(hex)) throw new Error("hex inválido");
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
  return out;
}

export function bytesToHex(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function concat(...parts) {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}

const PAYLOAD_LEN = 24, VERSION = 1, RESYNC_MAGIC = "RESYNC";

// Campos do payload (docs/PACOTE.md), so para conferencia e exibicao.
export function decodePayload(payload) {
  if (payload.length !== PAYLOAD_LEN) return null;
  const v = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  return { ver: v.getUint8(0), node_id: v.getUint16(1), seq: v.getUint32(3), ts: v.getUint32(7),
    temp_c: v.getInt16(11) / 100, hum_pct: v.getUint16(13) / 100, status: v.getUint8(15) };
}

async function checkBlock(b, payload, sig, keyFor, subtle) {
  if (b.kind === "resync") {
    const magic = String.fromCharCode(...payload.slice(0, 6));
    const node = payload.length === 12 ? new DataView(payload.buffer, payload.byteOffset).getUint16(6) : -1;
    const ok = payload.length === 12 && magic === RESYNC_MAGIC && node === b.node_id && sig.length === 0 && b.seq === 0;
    return ok ? null : "coluna_divergente";
  }
  if (b.kind !== "data") return "coluna_divergente";
  const key = await keyFor(b.node_id);
  if (!key || sig.length !== 64) return "assinatura_invalida";
  if (!(await subtle.verify({ name: "ECDSA", hash: "SHA-256" }, key, sig, payload))) return "assinatura_invalida";
  const r = decodePayload(payload);
  if (!r || r.ver !== VERSION || r.status > 2 || r.node_id !== b.node_id || r.seq !== b.seq) return "coluna_divergente";
  return null;
}

// Devolve { ok, checked, bad: {idx, reason} | null, blocks: [{idx, ok, reason}] }.
// Como o gateway, para no PRIMEIRO bloco invalido (os seguintes ficam sem veredito).
export async function verifyExport(doc, subtle = globalThis.crypto.subtle) {
  if (!doc || !Array.isArray(doc.blocks) || typeof doc.nodes !== "object") throw new Error("arquivo não é um export da corrente");
  const keys = new Map();
  const keyFor = async (nodeId) => {
    const id = String(nodeId);
    if (!keys.has(id)) {
      let key = null;
      try {
        if (doc.nodes[id]) key = await subtle.importKey("raw", hexToBytes(doc.nodes[id]), { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
      } catch (e) { key = null; }
      keys.set(id, key);
    }
    return keys.get(id);
  };
  const result = { ok: true, checked: 0, bad: null, blocks: [] };
  let prev = doc.genesis || "00".repeat(32);
  for (const b of doc.blocks) {
    let reason = null;
    try {
      const payload = hexToBytes(b.payload), sig = hexToBytes(b.sig);
      if (b.prev_hash !== prev) reason = "prev_hash_diferente";
      else {
        const digest = new Uint8Array(await subtle.digest("SHA-256", concat(hexToBytes(prev), payload, sig)));
        if (bytesToHex(digest) !== b.hash) reason = "hash_quebrado";
        else reason = await checkBlock(b, payload, sig, keyFor, subtle);
      }
    } catch (e) { reason = "coluna_divergente"; }
    result.checked++;
    result.blocks.push({ idx: b.idx, ok: !reason, reason });
    if (reason) { result.ok = false; result.bad = { idx: b.idx, reason }; break; }
    prev = b.hash;
  }
  return result;
}
