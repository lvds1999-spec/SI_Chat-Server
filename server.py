import base64
import os
import socket
import threading

from Protocolo.Rede.protocolo import (
    criar_entrega_mensagem,
    criar_aviso_digitando,
    criar_aviso_novo_dispositivo,
    criar_mensagem_status,
    criar_desafio_login,
    criar_resposta_chave_publica,
    criar_lista_contatos,
    criar_lista_usuarios,
    criar_mensagem,
    criar_resposta_adicionar_contato,
    criar_resposta_remover_contato,
    criar_resposta_logout,
    enviar_evento,
    ler_eventos,
)
from Protocolo.Rede.dominio.servico_chat import ServicoChat
from persistencia.repositorio_mensagens import RepositorioMensagens
from persistencia.repositorio_usuarios import RepositorioUsuarios
from persistencia.repositorio_contatos import RepositorioContatos
from src.seguranca import ErroSeguranca, SessaoSegura
from src.seguranca.assinatura import (
    chave_publica_corresponde,
    normalizar_chave_publica,
    verificar_assinatura,
)


HOST = "0.0.0.0"
PORTA = 8000

repositorio_usuarios = RepositorioUsuarios()
repositorio_mensagens = RepositorioMensagens()
repositorio_contatos = RepositorioContatos()
servico_chat = ServicoChat(repositorio_usuarios)
usuarios_online = {}
usuarios_online_lock = threading.Lock()
handshakes_realizados = set()
handshakes_lock = threading.Lock()
locks_usuarios = {}
locks_usuarios_lock = threading.Lock()


def _chave_handshake(usuario_a, usuario_b):
    return tuple(sorted((usuario_a, usuario_b)))


def _handshake_existe(remetente, destinatario):
    with handshakes_lock:
        return _chave_handshake(remetente, destinatario) in handshakes_realizados


def _registrar_handshake(remetente, destinatario):
    with handshakes_lock:
        handshakes_realizados.add(_chave_handshake(remetente, destinatario))


def _limpar_handshakes(usuario):
    with handshakes_lock:
        handshakes_realizados.difference_update(
            par for par in handshakes_realizados if usuario in par
        )


def _lock_usuario(usuario):
    with locks_usuarios_lock:
        return locks_usuarios.setdefault(usuario, threading.Lock())


def criar_lista_contatos_atualizada(usuario):
    with usuarios_online_lock:
        online = set(usuarios_online)

    contatos = repositorio_contatos.listar(usuario)

    return criar_lista_contatos([
        {
            "usuario": contato,
            "online": contato in online
        }
        for contato in contatos
    ])


def criar_lista_usuarios_atualizada():
    usuarios = repositorio_usuarios.listar_usuarios()

    with usuarios_online_lock:
        online = set(usuarios_online)

    return criar_lista_usuarios([
        {
            "usuario": usuario,
            "online": usuario in online
        }
        for usuario in usuarios
    ])


def transmitir_para_conectados(evento, ignorar=None):
    with usuarios_online_lock:
        clientes = list(usuarios_online.values())

    for cliente in clientes:
        if cliente is not ignorar:
            cliente.enviar(evento)


class ClientHandler(threading.Thread):

    def __init__(self, socket_cliente, endereco):
        super().__init__(daemon=True)

        self.socket_cliente = socket_cliente
        self.endereco = endereco

        self.arquivo = socket_cliente.makefile(
            "rwb"
        )
        self.usuario = None
        self.envio_lock = threading.Lock()
        self.sessao_segura = SessaoSegura("servidor")
        self.login_desafio = None

    def run(self):

        print(
            f"[NOVA CONEXÃO] "
            f"{self.endereco[0]}:{self.endereco[1]}"
        )

        try:
            self.sessao_segura.iniciar_servidor(self.arquivo)

            for evento in ler_eventos(self.arquivo, self.sessao_segura):

                print(
                    f"[RECEBIDO] "
                    f"{self.endereco}: {evento}"
                )

                self.processar_evento(evento)

        except (ConnectionError, OSError):

            print(
                f"[DESCONECTADO] "
                f"{self.endereco}"
            )

        except (ErroSeguranca, ValueError) as erro:

            print(
                f"[ERRO] "
                f"{self.endereco}: {erro}"
            )

        except Exception as erro:

            print(
                f"[ERRO] "
                f"{self.endereco}: {erro}"
            )

        finally:

            self.fechar()

    def processar_evento(self, evento):

        tipo = evento.get("evento")

        if tipo == "registro":
            algoritmo = evento.get("algoritmo_assinatura")
            chave_publica = evento.get("chave_publica")
            try:
                chave_publica = (
                    normalizar_chave_publica(algoritmo, chave_publica)
                    if chave_publica is not None
                    else None
                )
            except ValueError as erro:
                self.enviar({
                    "evento": "resposta_registro",
                    "sucesso": False,
                    "mensagem": str(erro),
                })
                return

            resposta = servico_chat.registrar_usuario(
                evento.get("usuario"),
                evento.get("senha"),
                chave_publica,
            )

            self.enviar(resposta)

            return

        if tipo in {
            "solicitar_chave_publica",
            "obter_chave_publica",
            "distribuir_chave_publica",
        }:
            if self.usuario is None:
                self.enviar(criar_resposta_chave_publica(
                    False,
                    evento.get("usuario"),
                    mensagem="É necessário fazer login antes de consultar chaves.",
                ))
                return

            usuario_alvo = evento.get(
                "usuario",
                evento.get("destinatario"),
            )
            chave = repositorio_usuarios.obter_chave_publica(usuario_alvo)
            if not chave or ":" not in chave:
                self.enviar(criar_resposta_chave_publica(
                    False,
                    usuario_alvo,
                    mensagem="Usuário não possui chave pública cadastrada.",
                ))
                return

            algoritmo, chave_publica = chave.split(":", 1)
            self.enviar(criar_resposta_chave_publica(
                True,
                usuario_alvo,
                algoritmo,
                chave_publica,
            ))
            return

        if tipo in {
            "handshake_concluido",
            "registrar_handshake",
            "handshake",
        }:
            if self.usuario is None:
                self.enviar({
                    "evento": "erro",
                    "codigo": "autenticacao_necessaria",
                    "mensagem": "É necessário fazer login antes do handshake.",
                })
                return

            destinatario = evento.get(
                "usuario",
                evento.get("destinatario"),
            )
            if not destinatario or not repositorio_usuarios.usuario_existe(
                destinatario
            ) or destinatario == self.usuario:
                self.enviar({
                    "evento": "erro",
                    "codigo": "destinatario_invalido",
                    "mensagem": "Destinatário de handshake inválido.",
                })
                return

            _registrar_handshake(self.usuario, destinatario)
            self.enviar({
                "evento": "handshake_confirmado",
                "usuario": destinatario,
            })
            return

        if tipo == "login":
            usuario = evento.get("usuario")
            senha = evento.get("senha")
            algoritmo = evento.get("algoritmo_assinatura")
            chave_publica = evento.get("chave_publica")

            if self.usuario is not None:
                self.enviar({
                    "evento": "resposta_login",
                    "sucesso": False,
                    "mensagem": "Esta conexão já está autenticada."
                })
                return

            try:
                chave_apresentada = normalizar_chave_publica(
                    algoritmo,
                    chave_publica,
                )
            except ValueError:
                self.enviar({
                    "evento": "resposta_login",
                    "sucesso": False,
                    "mensagem": "Chave pública e algoritmo são obrigatórios.",
                })
                return

            chave_atual = repositorio_usuarios.obter_chave_publica(usuario)
            if chave_publica_corresponde(
                chave_atual,
                algoritmo,
                chave_publica,
            ):
                nonce = os.urandom(32)
                self.login_desafio = {
                    "usuario": usuario,
                    "nonce": nonce,
                    "algoritmo_assinatura": algoritmo,
                    "chave_publica": chave_publica,
                }
                self.enviar(criar_desafio_login(
                    base64.b64encode(nonce).decode("ascii"),
                    algoritmo,
                ))
                return

            resposta = servico_chat.autenticar_usuario(usuario, senha)
            if not resposta["sucesso"]:
                self.enviar(resposta)
                return

            repositorio_usuarios.atualizar_chave_publica(
                usuario,
                chave_apresentada,
            )
            self._concluir_login(
                usuario,
                novo_dispositivo=chave_atual != chave_apresentada,
                algoritmo=algoritmo,
                chave_publica=chave_publica,
            )
            return

        if tipo == "login_assinatura":
            desafio = self.login_desafio
            self.login_desafio = None
            if desafio is None:
                self.enviar({
                    "evento": "resposta_login",
                    "sucesso": False,
                    "mensagem": "Nenhum desafio de login está pendente.",
                })
                return

            try:
                assinatura_valida = verificar_assinatura(
                    desafio["algoritmo_assinatura"],
                    desafio["chave_publica"],
                    desafio["nonce"],
                    evento.get("assinatura"),
                )
            except (ValueError, TypeError):
                assinatura_valida = False

            if not assinatura_valida:
                self.enviar({
                    "evento": "resposta_login",
                    "sucesso": False,
                    "mensagem": "Assinatura de login inválida.",
                })
                return

            self._concluir_login(
                desafio["usuario"],
                novo_dispositivo=False,
                algoritmo=desafio["algoritmo_assinatura"],
                chave_publica=desafio["chave_publica"],
            )

            return

        if tipo == "adicionar_contato":
            if self.usuario is None:
                self.enviar(criar_resposta_adicionar_contato(
                    False,
                    evento.get("contato"),
                    "É necessário fazer login antes de adicionar contatos."
                ))
                return

            contato_recebido = evento.get(
                "contato",
                evento.get("usuario", "")
            )
            contato = (
                contato_recebido.strip()
                if isinstance(contato_recebido, str)
                else ""
            )

            if not contato or contato == self.usuario:
                self.enviar(criar_resposta_adicionar_contato(
                    False,
                    contato,
                    "Contato inválido."
                ))
                return

            if not repositorio_usuarios.usuario_existe(contato):
                self.enviar(criar_resposta_adicionar_contato(
                    False,
                    contato,
                    "Contato não encontrado. Informe um usuário cadastrado."
                ))
                return

            with usuarios_online_lock:
                contato_online = contato in usuarios_online

            if not repositorio_contatos.adicionar(self.usuario, contato):
                self.enviar(criar_resposta_adicionar_contato(
                    False,
                    contato,
                    "Este contato já foi adicionado."
                ))
                return

            self.enviar(criar_resposta_adicionar_contato(
                True,
                contato,
                "Contato adicionado com sucesso.",
            ) | {"online": contato_online})
            self.enviar(criar_lista_contatos_atualizada(self.usuario))
            return

        if tipo == "remover_contato":
            contato = evento.get("contato", "").strip()

            if self.usuario is None:
                self.enviar(criar_resposta_remover_contato(
                    False,
                    contato,
                    "É necessário fazer login antes de remover contatos."
                ))
                return

            removido = repositorio_contatos.remover(self.usuario, contato)
            self.enviar(criar_resposta_remover_contato(
                removido,
                contato,
                "Contato removido com sucesso." if removido
                else "Contato não encontrado na sua lista."
            ))
            if removido:
                self.enviar(criar_lista_contatos_atualizada(self.usuario))
            return

        if tipo == "logout":
            usuario = self.usuario
            if usuario is not None:
                with _lock_usuario(usuario):
                    with usuarios_online_lock:
                        if usuarios_online.get(usuario) is self:
                            usuarios_online.pop(usuario)
                self.usuario = None
                transmitir_para_conectados({
                    "evento": "presenca",
                    "usuario": usuario,
                    "online": False
                })
            self.enviar(criar_resposta_logout("Logout realizado com sucesso."))
            return

        if tipo == "mensagem":
            return self._tratar_mensagem(evento)

        if tipo in ("digitando_inicio", "digitando_fim"):
            if self.usuario is None:
                return

            destinatario = evento.get("destinatario")
            with usuarios_online_lock:
                cliente_destinatario = usuarios_online.get(destinatario)

            if cliente_destinatario is not None:
                try:
                    cliente_destinatario.enviar(criar_aviso_digitando(
                        self.usuario,
                        destinatario,
                        tipo == "digitando_inicio"
                    ))
                except (ConnectionError, OSError):
                    with usuarios_online_lock:
                        removido = (
                            usuarios_online.get(destinatario)
                            is cliente_destinatario
                        )
                        if removido:
                            usuarios_online.pop(destinatario)

                    if removido:
                        transmitir_para_conectados({
                            "evento": "presenca",
                            "usuario": destinatario,
                            "online": False
                        })
            return

        resposta = {
            "evento": "evento_recebido",
            "tipo": tipo
        }

        self.enviar(resposta)

    def _tratar_mensagem(self, evento):
        if self.usuario is None:
            self.enviar({
                "evento": "erro",
                "mensagem": "É necessário fazer login antes de enviar mensagens."
            })
            return

        destinatario = evento.get("destinatario")
        if not destinatario or not repositorio_usuarios.usuario_existe(
            destinatario
        ):
            self.enviar({
                "evento": "erro",
                "mensagem": "Destinatário não encontrado."
            })
            return

        mensagem = dict(evento)
        mensagem["remetente"] = self.usuario
        mensagem["destinatario"] = destinatario

        with _lock_usuario(destinatario):
            with usuarios_online_lock:
                cliente_destinatario = usuarios_online.get(destinatario)

            if not _handshake_existe(self.usuario, destinatario):
                self.enviar({
                    "evento": "erro",
                    "codigo": "handshake_ausente",
                    "mensagem": (
                        "Não existe handshake prévio com o destinatário."
                    ),
                })
                return

            mensagem_id = repositorio_mensagens.adicionar(
                destinatario,
                mensagem,
                status="enviado",
            )
            mensagem["id"] = mensagem_id

            status = "enviado"
            if cliente_destinatario is not None:
                try:
                    cliente_destinatario.enviar(mensagem)
                except (ConnectionError, OSError):
                    with usuarios_online_lock:
                        if usuarios_online.get(destinatario) is cliente_destinatario:
                            usuarios_online.pop(destinatario)
                else:
                    repositorio_mensagens.marcar_status(mensagem_id, "entregue")
                    status = "entregue"

        self.enviar(criar_mensagem_status(mensagem_id, status))

        self.enviar(criar_entrega_mensagem(
            self.usuario,
            destinatario,
            evento.get("timestamp")
        ))

    def _concluir_login(
        self,
        usuario,
        novo_dispositivo,
        algoritmo,
        chave_publica,
    ):
        with _lock_usuario(usuario):
            with usuarios_online_lock:
                cliente_anterior = usuarios_online.get(usuario)
                usuarios_online[usuario] = self
                self.usuario = usuario

                if cliente_anterior is not None and cliente_anterior is not self:
                    cliente_anterior.usuario = None

            if novo_dispositivo:
                _limpar_handshakes(usuario)
                repositorio_mensagens.descartar_pendentes(usuario)
            else:
                mensagens_offline = repositorio_mensagens.listar_pendentes(
                    usuario
                )
                for mensagem_offline in mensagens_offline:
                    self.enviar(mensagem_offline)
                    repositorio_mensagens.marcar_status(
                        mensagem_offline["id"],
                        "entregue",
                    )
                    self._notificar_status(
                        mensagem_offline.get("remetente"),
                        mensagem_offline["id"],
                        "entregue",
                    )

        if cliente_anterior is not None and cliente_anterior is not self:
            cliente_anterior.fechar()

        self.enviar({
            "evento": "resposta_login",
            "sucesso": True,
            "mensagem": "Login realizado com sucesso.",
            "novo_dispositivo": novo_dispositivo,
        })
        self.enviar(criar_lista_usuarios_atualizada())
        self.enviar(criar_lista_contatos_atualizada(usuario))
        transmitir_para_conectados(
            {
                "evento": "presenca",
                "usuario": usuario,
                "online": True
            },
            ignorar=self,
        )

        if novo_dispositivo:
            self._avisar_novo_dispositivo(
                usuario,
                algoritmo,
                chave_publica,
            )
            return

    def _notificar_status(self, remetente, mensagem_id, status):
        if not remetente:
            return
        with usuarios_online_lock:
            cliente = usuarios_online.get(remetente)
        if cliente is None:
            return
        try:
            cliente.enviar(criar_mensagem_status(mensagem_id, status))
        except (ConnectionError, OSError):
            pass

    def _avisar_novo_dispositivo(self, usuario, algoritmo, chave_publica):
        aviso = criar_aviso_novo_dispositivo(
            usuario,
            algoritmo,
            chave_publica,
        )
        contatos = repositorio_contatos.listar(usuario)
        with usuarios_online_lock:
            clientes = [
                usuarios_online.get(contato)
                for contato in contatos
            ]

        for cliente in clientes:
            if cliente is not None:
                try:
                    cliente.enviar(aviso)
                except (ConnectionError, OSError):
                    pass

    def enviar(self, evento):
        with self.envio_lock:
            enviar_evento(self.arquivo, evento, self.sessao_segura)

    def fechar(self):

        usuario_desconectado = None
        if self.usuario is not None:
            usuario = self.usuario
            with _lock_usuario(usuario):
                with usuarios_online_lock:
                    if usuarios_online.get(usuario) is self:
                        usuarios_online.pop(usuario)
                        usuario_desconectado = usuario

        if usuario_desconectado is not None:
            transmitir_para_conectados({
                "evento": "presenca",
                "usuario": usuario_desconectado,
                "online": False
            })

        try:
            self.arquivo.close()
        except Exception:
            pass

        try:
            self.socket_cliente.close()
        except Exception:
            pass

        print(
            f"[CONEXÃO ENCERRADA] "
            f"{self.endereco}"
        )


def iniciar_servidor():

    servidor = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    # Permite reutilizar a porta rapidamente
    # após reiniciar o servidor.
    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    servidor.bind(
        (HOST, PORTA)
    )

    servidor.listen()

    print(
        "================================="
    )

    print(
        "SERVIDOR INICIADO"
    )

    print(
        f"Escutando em {HOST}:{PORTA}"
    )

    print(
        "Aguardando clientes..."
    )

    print(
        "================================="
    )

    try:

        while True:

            socket_cliente, endereco = (
                servidor.accept()
            )

            cliente = ClientHandler(
                socket_cliente,
                endereco
            )

            cliente.start()

    except KeyboardInterrupt:

        print(
            "\nServidor encerrado."
        )

    finally:

        servidor.close()


if __name__ == "__main__":
    iniciar_servidor()


