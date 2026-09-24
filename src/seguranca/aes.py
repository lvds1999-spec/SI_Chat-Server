from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


TAMANHO_CHAVE = 32
TAMANHO_NONCE = 16


def cifrar(chave, nonce, dados):
    if len(chave) != TAMANHO_CHAVE:
        raise ValueError("AES-256 exige uma chave de 32 bytes.")
    if len(nonce) != TAMANHO_NONCE:
        raise ValueError("AES-CTR exige um nonce de 16 bytes.")

    cifra = Cipher(algorithms.AES(chave), modes.CTR(nonce))
    return cifra.encryptor().update(dados)


def decifrar(chave, nonce, dados):
    return cifrar(chave, nonce, dados)
