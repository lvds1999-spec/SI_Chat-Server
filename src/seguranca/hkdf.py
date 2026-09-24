from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


TAMANHO_CHAVE = 32


def derivar_material(segredo, salt, contexto):
    """Deriva chaves direcionais de cifragem e autenticacao."""

    material = HKDF(
        algorithm=hashes.SHA256(),
        length=4 * TAMANHO_CHAVE,
        salt=salt,
        info=contexto,
    ).derive(segredo)

    return {
        "servidor_cifra": material[0:32],
        "servidor_mac": material[32:64],
        "cliente_cifra": material[64:96],
        "cliente_mac": material[96:128],
    }
