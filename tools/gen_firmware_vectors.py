"""Converte tests/vectors.json em firmware/test_vectors/vectors.h (vetores dourados em C).

Usado pelo firmware de teste (firmware/vectest) e pelo teste no PC (firmware/test_host).
A chave daqui e SOMENTE de teste e publica. Nunca usar na demonstracao.
Rodar depois de tools/gen_vectors.py: python tools/gen_firmware_vectors.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tests", "vectors.json")
DST = os.path.join(ROOT, "firmware", "test_vectors", "vectors.h")
GPS_INVALID = 0x7FFFFFFF


def c_bytes(data: bytes, indent: str = "    ") -> str:
    lines = []
    for i in range(0, len(data), 12):
        lines.append(indent + ", ".join(f"0x{b:02x}" for b in data[i : i + 12]) + ",")
    return "\n".join(lines)


def gps(v):
    return "CC_GPS_INVALID" if v is None else str(round(v * 1e6))


def main() -> None:
    with open(SRC) as f:
        data = json.load(f)
    priv = bytes.fromhex(data["private_key_hex"])
    pub = bytes.fromhex(data["public_key_hex"])
    assert pub[0] == 4 and len(pub) == 65
    out = [
        "// GERADO por tools/gen_firmware_vectors.py a partir de tests/vectors.json. Nao editar.",
        "// Chave de TESTE, publica. Nunca usar na demonstracao.",
        "#pragma once",
        "",
        '#include "cc_packet.h"',
        "",
        f"// curva: {data['curve']}",
        "static const uint8_t TEST_PRIV[32] = {",
        c_bytes(priv),
        "};",
        "// chave publica X||Y (sem o prefixo 0x04)",
        "static const uint8_t TEST_PUB[64] = {",
        c_bytes(pub[1:]),
        "};",
        "",
        "struct TestVector {",
        "  const char* note;",
        "  bool expect_valid;",
        "  bool has_reading;",
        "  CcReading reading;",
        "  float temp_c;",
        "  float hum_pct;",
        "  uint8_t packet[CC_PACKET_LEN];",
        "};",
        "",
        "static const TestVector TEST_VECTORS[] = {",
    ]
    for v in data["vectors"]:
        pkt = bytes.fromhex(v["packet_hex"])
        assert len(pkt) == 88
        note = v.get("note", "valido")
        r = v.get("reading")
        if r:
            reading = (
                f"{{{r['node_id']}, {r['seq']}u, {r['ts']}u, {round(r['temp_c'] * 100)}, "
                f"{round(r['hum_pct'] * 100)}, {r['status']}, {gps(r['lat'])}, {gps(r['lon'])}}}"
            )
            temps = f"{r['temp_c']}f, {r['hum_pct']}f"
        else:
            reading, temps = "{}", "0.0f, 0.0f"
        out += [
            "  {",
            f'    "{note}", {str(v["expect"] == "valid").lower()}, {str(bool(r)).lower()},',
            f"    {reading},",
            f"    {temps},",
            "    {",
            c_bytes(pkt, "      "),
            "    },",
            "  },",
        ]
    out += [
        "};",
        "static const size_t TEST_VECTOR_COUNT = sizeof(TEST_VECTORS) / sizeof(TEST_VECTORS[0]);",
        "",
    ]
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w") as f:
        f.write("\n".join(out))
    print("gerado:", DST, f"({len(data['vectors'])} vetores)")


if __name__ == "__main__":
    main()
