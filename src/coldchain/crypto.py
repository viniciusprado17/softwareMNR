"""ECDSA P-256 + SHA-256 com assinatura bruta r||s (64 bytes).

O formato bruto e o que o firmware (mbedTLS / micro-ecc) produz com facilidade;
a biblioteca `cryptography` usa DER, entao convertemos aqui.
"""
from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

CURVE = ec.SECP256R1()
_HASH = ec.ECDSA(hashes.SHA256())


def generate_keypair() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(CURVE)


def sign(private_key: ec.EllipticCurvePrivateKey, payload: bytes) -> bytes:
    der = private_key.sign(payload, _HASH)
    r, s = decode_dss_signature(der)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def verify(public_key: ec.EllipticCurvePublicKey, payload: bytes, sig: bytes) -> bool:
    if len(sig) != 64:
        return False
    r = int.from_bytes(sig[:32], "big")
    s = int.from_bytes(sig[32:], "big")
    try:
        public_key.verify(encode_dss_signature(r, s), payload, _HASH)
        return True
    except InvalidSignature:
        return False


def public_bytes_raw(public_key: ec.EllipticCurvePublicKey) -> bytes:
    """Chave publica nao comprimida (0x04 || X || Y, 65 bytes), util para o firmware."""
    return public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def public_from_raw(data: bytes) -> ec.EllipticCurvePublicKey:
    return ec.EllipticCurvePublicKey.from_encoded_point(CURVE, data)


def private_to_pem(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def private_from_pem(pem: bytes) -> ec.EllipticCurvePrivateKey:
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError("chave PEM nao e EC")
    return key
