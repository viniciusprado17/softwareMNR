// Metricas de cadeia de frio (static/metrics.js). Rodar: node --test tests/js/*.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";

import { countExcursions, meanKineticTemp } from "../../src/coldchain/static/metrics.js";

test("MKT de serie constante e a propria temperatura", () => {
  assert.ok(Math.abs(meanKineticTemp([5, 5, 5, 5]) - 5) < 1e-9);
});

test("MKT de serie alternada bate com a formula calculada a parte", () => {
  const k = (c) => c + 273.15;
  const expected = 10000 / -Math.log((Math.exp(-10000 / k(0)) + Math.exp(-10000 / k(10))) / 2) - 273.15;
  assert.ok(Math.abs(meanKineticTemp([0, 10, 0, 10]) - expected) < 1e-9);
  assert.ok(expected > 5, "MKT pesa mais as temperaturas altas que a media simples");
});

test("MKT sem leituras e null", () => {
  assert.equal(meanKineticTemp([]), null);
});

test("excursoes contam trechos contiguos fora da faixa", () => {
  assert.equal(countExcursions([5, 9, 9, 5, 1, 5], 2, 8), 2);
  assert.equal(countExcursions([5, 6, 7], 2, 8), 0);
  assert.equal(countExcursions([9, 9, 9], 2, 8), 1);
  assert.equal(countExcursions([], 2, 8), 0);
});
