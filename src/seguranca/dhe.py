from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)


class ParChavesDHE:
    """Par de chaves efemeras para Diffie-Hellman sobre Curve25519."""

    def __init__(self, privada):
        self._privada = privada

    @classmethod
    def gerar(cls):
        return cls(X25519PrivateKey.generate())

    @property
    def publica(self):
        return self._privada.public_key().public_bytes_raw()

    def derivar_segredo(self, publica_remota):
        chave_remota = X25519PublicKey.from_public_bytes(publica_remota)
        return self._privada.exchange(chave_remota)
