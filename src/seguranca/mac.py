import hmac

TAMANHO_TAG = 32


def gerar_tag(chave, dados):
    return hmac.digest(chave, dados, "sha256")


def verificar_tag(chave, dados, tag):
    esperada = gerar_tag(chave, dados)
    return hmac.compare_digest(esperada, tag)
