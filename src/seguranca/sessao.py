import base64
import hashlib
import json
import os
import struct
import threading
import time

from .aes import cifrar, decifrar
from .dhe import ParChavesDHE
from .hkdf import derivar_material
from .mac import gerar_tag, verificar_tag


VERSAO = 1
TAMANHO_MAXIMO_ENVELOPE = 2 * 1024 * 1024
INTERVALO_RENOVACAO = 60 * 60
LIMITE_MENSAGENS = 100


class ErroSeguranca(Exception):
    pass


def _b64(dados):
    return base64.b64encode(dados).decode("ascii")


def _de_b64(valor):
    if not isinstance(valor, str):
        raise ErroSeguranca("Campo binario ausente no envelope.")
    try:
        return base64.b64decode(valor.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as erro:
        raise ErroSeguranca("Campo binario invalido no envelope.") from erro


def _escrever_linha(arquivo, objeto):
    dados = (json.dumps(objeto, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    arquivo.write(dados)
    arquivo.flush()


def _ler_linha(arquivo):
    linha = arquivo.readline()
    if not linha:
        raise ConnectionError("Conexao encerrada durante o handshake.")
    if len(linha) > TAMANHO_MAXIMO_ENVELOPE:
        raise ErroSeguranca("Mensagem maior que o limite permitido.")
    try:
        objeto = json.loads(linha.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroSeguranca("Mensagem de transporte malformada.") from erro
    if not isinstance(objeto, dict):
        raise ErroSeguranca("Mensagem de transporte invalida.")
    return objeto


class SessaoSegura:
    """Transporte autenticado com DHE efemero e renovacao de chaves."""

    def __init__(self, papel):
        if papel not in {"servidor", "cliente"}:
            raise ValueError("O papel deve ser servidor ou cliente.")
        self.papel = papel
        self._chaves = None
        self._sequencia_envio = 0
        self._sequencia_recebimento = 0
        self._mensagens = 0
        self._inicio = 0.0
        self._lock = threading.RLock()

    def iniciar_servidor(self, arquivo):
        with self._lock:
            par = ParChavesDHE.gerar()
            nonce_servidor = os.urandom(16)
            _escrever_linha(arquivo, {
                "evento": "handshake_servidor",
                "versao": VERSAO,
                "chave_publica": _b64(par.publica),
                "nonce": _b64(nonce_servidor),
            })
            resposta = _ler_linha(arquivo)
            self._validar_tipo(resposta, "handshake_cliente")
            self._estabelecer(
                par,
                _de_b64(resposta.get("chave_publica")),
                nonce_servidor,
                _de_b64(resposta.get("nonce")),
            )

    def iniciar_cliente(self, arquivo):
        with self._lock:
            convite = _ler_linha(arquivo)
            self._validar_tipo(convite, "handshake_servidor")
            par = ParChavesDHE.gerar()
            nonce_cliente = os.urandom(16)
            _escrever_linha(arquivo, {
                "evento": "handshake_cliente",
                "versao": VERSAO,
                "chave_publica": _b64(par.publica),
                "nonce": _b64(nonce_cliente),
            })
            self._estabelecer(
                par,
                _de_b64(convite.get("chave_publica")),
                _de_b64(convite.get("nonce")),
                nonce_cliente,
            )

    def enviar(self, arquivo, dados):
        with self._lock:
            self._exigir_estabelecida()
            envelope = self._criar_envelope(dados)
            _escrever_linha(arquivo, envelope)

    def receber(self, arquivo):
        self._exigir_estabelecida()
        while True:
            envelope = _ler_linha(arquivo)
            with self._lock:
                dados = self._abrir_envelope(envelope)
            evento = json.loads(dados.decode("utf-8"))
            if not isinstance(evento, dict):
                raise ErroSeguranca("Evento cifrado invalido.")
            if evento.get("evento") == "renovacao_servidor":
                if self.papel != "cliente":
                    raise ErroSeguranca("Renovacao inesperada.")
                with self._lock:
                    self._responder_renovacao(arquivo, evento)
                continue
            if self.papel == "servidor" and self.deve_renovar():
                with self._lock:
                    self._renovar_servidor(arquivo)
            return dados

    def deve_renovar(self):
        return (
            self._mensagens >= LIMITE_MENSAGENS
            or time.monotonic() - self._inicio >= INTERVALO_RENOVACAO
        )

    def _estabelecer(self, par, publica_remota, nonce_servidor, nonce_cliente):
        if len(publica_remota) != 32:
            raise ErroSeguranca("Chave publica DHE invalida.")
        if len(nonce_servidor) != 16 or len(nonce_cliente) != 16:
            raise ErroSeguranca("Nonce de handshake invalido.")
        segredo = par.derivar_segredo(publica_remota)
        salt = hashlib.sha256(nonce_servidor + nonce_cliente).digest()
        self._chaves = derivar_material(
            segredo,
            salt,
            b"SI_Chat-Server transporte seguro v1",
        )
        self._sequencia_envio = 0
        self._sequencia_recebimento = 0
        self._mensagens = 0
        self._inicio = time.monotonic()

    def _criar_envelope(self, dados):
        nonce = os.urandom(16)
        sequencia = self._sequencia_envio
        cifrado = cifrar(self._chaves["servidor_cifra"], nonce, dados)
        if self.papel == "cliente":
            cifrado = cifrar(self._chaves["cliente_cifra"], nonce, dados)
        autenticado = struct.pack(">Q", sequencia) + nonce + cifrado
        mac_key = self._chaves[f"{self.papel}_mac"]
        envelope = {
            "evento": "envelope_seguro",
            "versao": VERSAO,
            "sequencia": sequencia,
            "nonce": _b64(nonce),
            "dados": _b64(cifrado),
            "tag": _b64(gerar_tag(mac_key, autenticado)),
        }
        self._sequencia_envio += 1
        self._mensagens += 1
        return envelope

    def _abrir_envelope(self, envelope):
        self._validar_tipo(envelope, "envelope_seguro")
        if envelope.get("versao") != VERSAO:
            raise ErroSeguranca("Versao de transporte nao suportada.")
        sequencia = envelope.get("sequencia")
        if sequencia != self._sequencia_recebimento:
            raise ErroSeguranca("Sequencia de transporte invalida.")
        nonce = _de_b64(envelope.get("nonce"))
        cifrado = _de_b64(envelope.get("dados"))
        tag = _de_b64(envelope.get("tag"))
        if len(nonce) != 16 or len(tag) != 32:
            raise ErroSeguranca("Envelope criptografico invalido.")
        autenticado = struct.pack(">Q", sequencia) + nonce + cifrado
        mac_key = self._chaves[f"{self._papel_remoto()}_mac"]
        if not verificar_tag(mac_key, autenticado, tag):
            raise ErroSeguranca("Autenticacao do envelope falhou.")
        cifra_key = self._chaves[f"{self._papel_remoto()}_cifra"]
        dados = decifrar(cifra_key, nonce, cifrado)
        self._sequencia_recebimento += 1
        self._mensagens += 1
        return dados

    def _renovar_servidor(self, arquivo):
        par = ParChavesDHE.gerar()
        nonce_servidor = os.urandom(16)
        self._enviar_controle(arquivo, {
            "evento": "renovacao_servidor",
            "versao": VERSAO,
            "chave_publica": _b64(par.publica),
            "nonce": _b64(nonce_servidor),
        })
        resposta = self._abrir_envelope(_ler_linha(arquivo))
        resposta = json.loads(resposta.decode("utf-8"))
        self._validar_tipo(resposta, "renovacao_cliente")
        self._estabelecer(
            par,
            _de_b64(resposta.get("chave_publica")),
            nonce_servidor,
            _de_b64(resposta.get("nonce")),
        )

    def _responder_renovacao(self, arquivo, controle):
        self._validar_tipo(controle, "renovacao_servidor")
        par = ParChavesDHE.gerar()
        nonce_cliente = os.urandom(16)
        self._enviar_controle(arquivo, {
            "evento": "renovacao_cliente",
            "versao": VERSAO,
            "chave_publica": _b64(par.publica),
            "nonce": _b64(nonce_cliente),
        })
        self._estabelecer(
            par,
            _de_b64(controle.get("chave_publica")),
            _de_b64(controle.get("nonce")),
            nonce_cliente,
        )

    def _enviar_controle(self, arquivo, evento):
        _escrever_linha(arquivo, self._criar_envelope(
            json.dumps(evento, separators=(",", ":")).encode("utf-8")
        ))

    def _papel_remoto(self):
        return "cliente" if self.papel == "servidor" else "servidor"

    def _exigir_estabelecida(self):
        if self._chaves is None:
            raise ErroSeguranca("Handshake ainda nao foi concluido.")

    @staticmethod
    def _validar_tipo(objeto, tipo):
        if objeto.get("evento") != tipo or objeto.get("versao") != VERSAO:
            raise ErroSeguranca("Mensagem de handshake invalida.")
