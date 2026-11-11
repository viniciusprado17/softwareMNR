// Paridade entre o verificador do navegador e o Ledger.verify_chain do gateway.
// Rodar: node --test tests/js/
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { hexToBytes, verifyExport } from "../../src/coldchain/static/verifier-core.js";

const here = new URL(".", import.meta.url);
const cases = JSON.parse(readFileSync(new URL("../fixtures/verifier_cases.json", here))).cases;
const vectors = JSON.parse(readFileSync(new URL("../vectors.json", here)));

for (const c of cases) {
  test(`paridade com o Python: ${c.name}`, async () => {
    const r = await verifyExport(c.doc);
    assert.equal(r.ok, c.expected.ok);
    assert.equal(r.bad ? r.bad.idx : null, c.expected.bad_idx);
    assert.equal(r.bad ? r.bad.reason : null, c.expected.reason);
  });
}

test("cobre todos os motivos de falha", () => {
  const reasons = new Set(cases.map((c) => c.expected.reason));
  for (const r of ["prev_hash_diferente", "hash_quebrado", "assinatura_invalida", "coluna_divergente", null]) {
    assert.ok(reasons.has(r), `falta caso para ${r}`);
  }
});

test("vetores dourados: WebCrypto aceita os validos e rejeita os invalidos", async () => {
  const key = await crypto.subtle.importKey("raw", hexToBytes(vectors.public_key_hex),
    { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
  for (const v of vectors.vectors) {
    const ok = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, key, hexToBytes(v.sig_hex), hexToBytes(v.payload_hex));
    assert.equal(ok, v.expect === "valid");
  }
});

test("arquivo que nao e export e recusado", async () => {
  await assert.rejects(() => verifyExport({ foo: 1 }));
});
