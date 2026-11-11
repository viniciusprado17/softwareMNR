// Metricas de cadeia de frio calculadas so a partir das leituras exibidas (sem DOM).
// Testadas em tests/js/metrics.test.mjs.

// dH/R da temperatura cinetica media (MKT): 83,144 kJ/mol / 8,3144 J/(mol.K) = 10000 K.
export const MKT_DH_R = 10000;

// MKT em graus C, com pesos iguais para todas as leituras. Lista vazia -> null.
export function meanKineticTemp(temps, dhr = MKT_DH_R) {
  if (!temps.length) return null;
  const sum = temps.reduce((acc, t) => acc + Math.exp(-dhr / (t + 273.15)), 0);
  return dhr / -Math.log(sum / temps.length) - 273.15;
}

// Numero de trechos contiguos fora da faixa [low, high].
export function countExcursions(temps, low, high) {
  let n = 0, out = false;
  for (const t of temps) {
    const now = t < low || t > high;
    if (now && !out) n++;
    out = now;
  }
  return n;
}
