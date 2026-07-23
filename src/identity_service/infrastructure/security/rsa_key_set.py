import base64
import hashlib
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _base64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8 or 1, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class RsaKeySet:
    def __init__(self, private_key_pem: str) -> None:
        loaded = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        if not isinstance(loaded, rsa.RSAPrivateKey):
            raise ValueError("jwt signing key must be an RSA private key")
        self._private_key = loaded
        self._public_key = loaded.public_key()
        numbers = self._public_key.public_numbers()
        self._modulus = _base64url_uint(numbers.n)
        self._exponent = _base64url_uint(numbers.e)
        thumbprint_input = json.dumps(
            {"e": self._exponent, "kty": "RSA", "n": self._modulus},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        digest = hashlib.sha256(thumbprint_input).digest()
        self._key_id = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        return self._private_key

    @property
    def public_key(self) -> rsa.RSAPublicKey:
        return self._public_key

    @property
    def key_id(self) -> str:
        return self._key_id

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self._key_id,
                    "n": self._modulus,
                    "e": self._exponent,
                }
            ]
        }
