"""Teste ponta a ponta do prototipo, conduzido pela API do gateway (Secao 10.5).

Pre-requisito: o gateway rodando com os botoes de demonstracao, por exemplo
  run_gateway.bat --port COM3 --demo-controls        (hardware real)
  run_gateway.bat                                   (simulado, para ensaio)

Uso (outro PowerShell, na pasta do projeto):
  python tools/teste_ponta_a_ponta.py
  python tools/teste_ponta_a_ponta.py --pacotes 6 --mao      (inclui o teste da mao no sensor)

O que confere, em ordem:
  1. gateway no ar, com botoes de demonstracao e (se hardware) serial conectada
  2. Restaurar demo (corrente vazia)
  3. N pacotes reais ACEITOS chegando pelo radio (seq crescente, RSSI/SNR)
  4. (opcional) mao no sensor: a temperatura sobe
  5. pacote adulterado -> assinatura_invalida
  6. pacote reenviado -> replay
  7. corrente integra -> Verificar corrente OK
  8. banco adulterado -> Verificar corrente acusa o bloco
  9. Restaurar demo no fim (deixa a tela limpa para a apresentacao)

Gera um relatorio em logs/teste_ponta_a_ponta_<data>.txt. So usa a biblioteca padrao.
Mede apenas o que viu: taxa de entrega = blocos aceitos / seq enviados no periodo.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def _call(self, method: str, path: str):
        req = urllib.request.Request(self.base + path, method=method, data=b"" if method == "POST" else None)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode() or "null")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {body}") from None

    def get(self, path: str):
        return self._call("GET", path)

    def post(self, path: str):
        return self._call("POST", path)


class Relatorio:
    def __init__(self):
        self.linhas: list[str] = []
        self.resultados: list[tuple[str, bool, str]] = []

    def log(self, msg: str = ""):
        print(msg, flush=True)
        self.linhas.append(msg)

    def item(self, nome: str, ok: bool, detalhe: str = ""):
        self.resultados.append((nome, ok, detalhe))
        self.log(f"  [{'OK   ' if ok else 'FALHA'}] {nome}" + (f": {detalhe}" if detalhe else ""))


def esperar_pacotes(api: Api, rel: Relatorio, n: int, timeout: float) -> list[dict]:
    rel.log(f"\nEsperando {n} pacotes aceitos (ate {timeout:.0f} s; o no manda a cada ~10 s)...")
    vistos: dict[int, dict] = {}
    fim = time.time() + timeout
    while time.time() < fim and len(vistos) < n:
        for r in api.get("/api/readings?limit=50"):
            if r["idx"] not in vistos:
                vistos[r["idx"]] = r
                rssi = "--" if r["rssi"] is None else f"{r['rssi']} dBm"
                snr = "--" if r["snr"] is None else f"{r['snr']} dB"
                gps = "sem fix" if r["lat"] is None else f"{r['lat']:.5f},{r['lon']:.5f}"
                rel.log(f"  bloco {r['idx']}: seq {r['seq']}  {r['temp_c']:.2f} C  {r['hum_pct']:.1f} %"
                        f"  {r['status_name']}  RSSI {rssi}  SNR {snr}  GPS {gps}")
        time.sleep(1)
    return sorted(vistos.values(), key=lambda r: r["idx"])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://127.0.0.1:8000", help="endereco da tela do gateway")
    p.add_argument("--pacotes", type=int, default=3, help="pacotes reais a esperar (padrao 3)")
    p.add_argument("--timeout", type=float, default=0, help="segundos de espera (padrao: 15 s por pacote + 20)")
    p.add_argument("--mao", action="store_true", help="inclui o teste de segurar o sensor com a mao")
    p.add_argument("--sem-restaurar-fim", action="store_true", help="nao limpa a corrente no fim")
    args = p.parse_args(argv)
    api = Api(args.url)
    rel = Relatorio()
    inicio = time.strftime("%Y-%m-%d %H:%M:%S")
    rel.log(f"Teste ponta a ponta MNR 2026, {inicio}, gateway {args.url}")

    # 1. Gateway no ar
    try:
        st = api.get("/api/status")
    except Exception as e:  # noqa: BLE001
        rel.log(f"\nERRO: gateway fora do ar ({e}).")
        rel.log("Abra antes, em outro PowerShell:  .\\run_gateway.bat --port COM3 --demo-controls")
        return 2
    modo = "SIMULADO" if st["simulate"] else f"HARDWARE ({st['serial'].get('source') or 'serial'})"
    rel.log(f"Modo: {modo}")
    if st["simulate"]:
        rel.log("ATENCAO: modo simulado. Este teste NAO comprova o hardware.")
    rel.log("\n1. Gateway")
    rel.item("gateway no ar", True)
    rel.item("botoes de demonstracao ligados", st["demo_controls"],
             "" if st["demo_controls"] else "abra com --demo-controls")
    if not st["demo_controls"]:
        return finalizar(rel, args)
    if not st["simulate"]:
        rel.item("serial da receptora conectada", st["serial"]["connected"],
                 "" if st["serial"]["connected"] else "confira cabo/porta e se outro programa usa a COM")

    # 2. Corrente vazia
    rel.log("\n2. Restaurar demo")
    api.post("/api/demo/reset")
    st = api.get("/api/status")
    rel.item("corrente vazia", st["chain"]["blocks"] == 0, f"{st['chain']['blocks']} blocos")

    # 3. Pacotes reais
    rel.log("\n3. Pacotes pelo radio")
    timeout = args.timeout or 15 * args.pacotes + 20
    t0 = time.time()
    pkts = esperar_pacotes(api, rel, args.pacotes, timeout)
    dt = time.time() - t0
    rel.item(f"{args.pacotes} pacotes aceitos", len(pkts) >= args.pacotes,
             f"{len(pkts)} em {dt:.0f} s" + ("" if pkts else "; transmissora ligada? antena? TX ok no OLED?"))
    if not pkts:
        return finalizar(rel, args)
    seqs = [r["seq"] for r in pkts]
    crescente = all(b > a for a, b in zip(seqs, seqs[1:]))
    rel.item("seq crescente", crescente, " -> ".join(map(str, seqs)))
    enviados = seqs[-1] - seqs[0] + 1
    rel.item("taxa de entrega no periodo", True,
             f"{len(pkts)}/{enviados} = {100 * len(pkts) / enviados:.0f} % (seq {seqs[0]} a {seqs[-1]})")
    rssis = [r["rssi"] for r in pkts if r["rssi"] is not None]
    if rssis:
        rel.item("RSSI medido", True, f"media {statistics.mean(rssis):.1f} dBm, min {min(rssis)}, max {max(rssis)}")

    # 4. Mao no sensor
    if args.mao:
        rel.log("\n4. Mao no sensor")
        base = pkts[-1]["temp_c"]
        input(f"  Temperatura agora: {base:.2f} C. Segure o SHT31 com a mao e aperte ENTER...")
        maior = base
        fim = time.time() + 45
        while time.time() < fim:
            ultimo = api.get("/api/readings?limit=1")
            if ultimo:
                maior = max(maior, ultimo[-1]["temp_c"])
            if maior >= base + 0.5:
                break
            time.sleep(2)
        rel.item("temperatura subiu", maior >= base + 0.5, f"{base:.2f} -> {maior:.2f} C")
        print("  Pode soltar o sensor.")

    # 5. Adulteracao
    rel.log("\n5. Ataques")
    r = api.post("/api/demo/tamper")
    rel.item("pacote adulterado rejeitado", r["result"] == "assinatura_invalida",
             f"{r['original_temp']:.2f} -> {r['forged_temp']:.2f} C: {r['result']}")
    # 6. Replay
    r = api.post("/api/demo/replay")
    rel.item("pacote reenviado rejeitado", r["result"] == "replay", f"seq {r['seq']}: {r['result']}")

    # 7/8. Corrente
    rel.log("\n6. Corrente de hash")
    v = api.get("/api/chain/verify")
    rel.item("corrente integra antes do ataque", v["ok"], v.get("motivo") or "")
    blocos = api.get("/api/status")["chain"]["blocks"]
    if blocos >= 2:
        c = api.post("/api/demo/corrupt-db")
        v = api.get("/api/chain/verify")
        rel.item("banco adulterado detectado", (not v["ok"]) and v["bloco_invalido"] == c["idx"],
                 f"bloco {c['idx']} {c['from_temp']:.2f} -> {c['to_temp']:.2f} C; "
                 f"verificacao: {v.get('motivo')} no bloco {v.get('bloco_invalido')}")
    else:
        rel.item("banco adulterado detectado", False, "precisa de pelo menos 2 blocos")

    return finalizar(rel, args, api)


def finalizar(rel: Relatorio, args, api: Api | None = None) -> int:
    if api and not args.sem_restaurar_fim:
        api.post("/api/demo/reset")
        rel.log("\nCorrente restaurada (tela limpa).")
    ok = sum(1 for _, b, _ in rel.resultados if b)
    total = len(rel.resultados)
    falhas = [n for n, b, _ in rel.resultados if not b]
    rel.log("\n" + "=" * 60)
    rel.log(f"RESULTADO: {ok}/{total} OK" + ("" if not falhas else f"  | FALHAS: {', '.join(falhas)}"))
    rel.log("=" * 60)
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    nome = os.path.join(ROOT, "logs", time.strftime("teste_ponta_a_ponta_%Y-%m-%d_%H-%M-%S.txt"))
    with open(nome, "w", encoding="utf-8") as f:
        f.write("\n".join(rel.linhas) + "\n")
    print(f"Relatorio salvo em {nome}")
    return 0 if not falhas and total else 1


if __name__ == "__main__":
    sys.exit(main())
