import base64
import binascii

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import (
    ed25519,
    padding,
    rsa,
)


ALGORITMOS = {"ed25519", "rsa-pss"}


def normalizar_chave_publica(algoritmo, chave_base64):
    if algoritmo not in ALGORITMOS or not isinstance(chave_base64, str):
        raise ValueError("Algoritmo ou chave publica invalido.")
    try:
        dados = base64.b64decode(chave_base64.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as erro:
        raise ValueError("Chave publica invalida.") from erro

    if algoritmo == "ed25519":
        if len(dados) != 32:
            raise ValueError("Chave Ed25519 invalida.")
        ed25519.Ed25519PublicKey.from_public_bytes(dados)
    else:
        chave = serialization.load_der_public_key(dados)
        if not isinstance(chave, rsa.RSAPublicKey) or chave.key_size < 2048:
            raise ValueError("Chave RSA deve ter pelo menos 2048 bits.")

    return f"{algoritmo}:{chave_base64}"


def chave_publica_corresponde(chave_persistida, algoritmo, chave_base64):
    try:
        return chave_persistida == normalizar_chave_publica(
            algoritmo,
            chave_base64,
        )
    except ValueError:
        return False


def verificar_assinatura(algoritmo, chave_base64, mensagem, assinatura_base64):
    if not isinstance(assinatura_base64, str):
        raise ValueError("Assinatura invalida.")
    chave_normalizada = normalizar_chave_publica(algoritmo, chave_base64)
    _, chave_codificada = chave_normalizada.split(":", 1)
    chave_der = base64.b64decode(chave_codificada.encode("ascii"))
    assinatura = base64.b64decode(
        assinatura_base64.encode("ascii"),
        validate=True,
    )

    if algoritmo == "ed25519":
        chave = ed25519.Ed25519PublicKey.from_public_bytes(chave_der)
        try:
            chave.verify(assinatura, mensagem)
        except InvalidSignature:
            return False
        return True

    chave = serialization.load_der_public_key(chave_der)
    try:
        chave.verify(
            assinatura,
            mensagem,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return False
    return True
