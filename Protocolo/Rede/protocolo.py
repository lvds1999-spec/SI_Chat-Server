import json


REGISTRO = "registro"
RESPOSTA_REGISTRO = "resposta_registro"

LOGIN = "login"
RESPOSTA_LOGIN = "resposta_login"
LOGOUT = "logout"
RESPOSTA_LOGOUT = "resposta_logout"

LISTA_CONTATOS = "lista_contatos"
ADICIONAR_CONTATO = "adicionar_contato"
RESPOSTA_ADICIONAR_CONTATO = "resposta_adicionar_contato"
REMOVER_CONTATO = "remover_contato"
RESPOSTA_REMOVER_CONTATO = "resposta_remover_contato"

MENSAGEM = "mensagem"
ENTREGA_MENSAGEM = "entrega_mensagem"

DIGITANDO_INICIO = "digitando_inicio"
DIGITANDO_FIM = "digitando_fim"
AVISO_DIGITANDO = "aviso_digitando"

PRESENCA = "presenca"

FILA_OFFLINE = "fila_offline"


def serializar(evento):
    """
    Converte um dicionário Python para JSON.

    O \\n no final permite que o servidor e o cliente
    saibam onde termina cada evento.
    """

    return (json.dumps(evento, ensure_ascii=False) + "\n").encode("utf-8")


def desserializar(dados):
    """
    Converte JSON recebido pela rede para um dicionário Python.
    """

    return json.loads(dados.decode("utf-8"))


def criar_registro(usuario, senha):
    return {
        "evento": REGISTRO,
        "usuario": usuario,
        "senha": senha
    }


def criar_resposta_registro(sucesso, mensagem):
    return {
        "evento": RESPOSTA_REGISTRO,
        "sucesso": sucesso,
        "mensagem": mensagem
    }


def criar_login(usuario, senha):
    return {
        "evento": LOGIN,
        "usuario": usuario,
        "senha": senha
    }


def criar_resposta_login(sucesso, mensagem):
    return {
        "evento": RESPOSTA_LOGIN,
        "sucesso": sucesso,
        "mensagem": mensagem
    }


def criar_lista_contatos(contatos):
    return {
        "evento": LISTA_CONTATOS,
        "contatos": contatos
    }


def criar_adicionar_contato(contato):
    return {
        "evento": ADICIONAR_CONTATO,
        "contato": contato
    }


def criar_resposta_adicionar_contato(sucesso, contato, mensagem):
    return {
        "evento": RESPOSTA_ADICIONAR_CONTATO,
        "sucesso": sucesso,
        "contato": contato,
        "mensagem": mensagem
    }


def criar_mensagem(remetente, destinatario, timestamp, texto):
    return {
        "evento": MENSAGEM,
        "remetente": remetente,
        "destinatario": destinatario,
        "timestamp": timestamp,
        "texto": texto
    }


def criar_entrega_mensagem(remetente, destinatario, timestamp):
    return {
        "evento": ENTREGA_MENSAGEM,
        "remetente": remetente,
        "destinatario": destinatario,
        "timestamp": timestamp
    }



def criar_inicio_digitacao(remetente, destinatario):
    return {
        "evento": DIGITANDO_INICIO,
        "remetente": remetente,
        "destinatario": destinatario
    }


def criar_fim_digitacao(remetente, destinatario):
    return {
        "evento": DIGITANDO_FIM,
        "remetente": remetente,
        "destinatario": destinatario
    }


def criar_aviso_digitando(remetente, destinatario, digitando):
    return {
        "evento": AVISO_DIGITANDO,
        "remetente": remetente,
        "destinatario": destinatario,
        "digitando": digitando
    }



def criar_presenca(usuario, online):
    return {
        "evento": PRESENCA,
        "usuario": usuario,
        "online": online
    }



def criar_fila_offline(mensagens):
    return {
        "evento": FILA_OFFLINE,
        "mensagens": mensagens
    }


def criar_remover_contato(contato):
    return {
        "evento": REMOVER_CONTATO,
        "contato": contato
    }


def criar_resposta_remover_contato(sucesso, contato, mensagem):
    return {
        "evento": RESPOSTA_REMOVER_CONTATO,
        "sucesso": sucesso,
        "contato": contato,
        "mensagem": mensagem
    }


def criar_logout():
    return {"evento": LOGOUT}


def criar_resposta_logout(mensagem):
    return {
        "evento": RESPOSTA_LOGOUT,
        "mensagem": mensagem
    }