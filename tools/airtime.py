"""Tempo no ar teorico de um pacote LoRa (formula da Semtech, AN1200.13), Secao 6.5.

Rodar: python tools/airtime.py [--bytes 88] [--interval 10]
Valores TEORICOS: medir na placa (linha INFO,...,tx_us do firmware do no) para o artigo.
"""
import argparse
import math


def time_on_air_ms(
    payload: int, sf: int, bw_khz: float = 125.0, cr: int = 5, preamble: int = 8,
    explicit_header: bool = True, crc: bool = True,
) -> float:
    t_sym = (2**sf) / (bw_khz * 1000) * 1000  # ms
    de = 1 if (sf >= 11 and bw_khz <= 125) else 0  # low data rate optimize
    ih = 0 if explicit_header else 1
    num = 8 * payload - 4 * sf + 28 + 16 * crc - 20 * ih
    n_payload = 8 + max(math.ceil(num / (4 * (sf - 2 * de))) * cr, 0)
    return (preamble + 4.25) * t_sym + n_payload * t_sym


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bytes", type=int, default=88)
    p.add_argument("--interval", type=float, default=10.0, help="intervalo de envio em s")
    args = p.parse_args()
    print(f"Pacote de {args.bytes} bytes, BW 125 kHz, CR 4/5, preambulo 8, cabecalho explicito, CRC")
    print(f"{'SF':>4} {'tempo no ar':>12} {'ocupacao @ ' + str(args.interval) + ' s':>18}")
    for sf in range(7, 13):
        t = time_on_air_ms(args.bytes, sf)
        print(f"{sf:>4} {t:>9.1f} ms {100 * t / (args.interval * 1000):>16.2f} %")


if __name__ == "__main__":
    main()
