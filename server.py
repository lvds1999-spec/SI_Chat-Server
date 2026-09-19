import socket
import threading

from Protocolo.Rede.protocolo import (
    criar_entrega_mensagem,
    criar_lista_contatos,
    criar_mensagem,
    criar_fila_offline,
    desserializar,
    serializar
)
from Protocolo.Rede.dominio.servico_chat import ServicoChat
from persistencia.repositorio_mensagens import RepositorioMensagens
from persistencia.repositorio_usuarios import RepositorioUsuarios


HOST = "0.0.0.0"
PORTA = 8000

repositorio_usuarios = RepositorioUsuarios()
repositorio_mensagens = RepositorioMensagens()
servico_chat = ServicoChat(repositorio_usuarios)
usuarios_online = {}
usuarios_online_lock = threading.Lock()


def criar_lista_contatos_atualizada():
    with usuarios_online_lock:
        online = set(usuarios_online)

    return criar_lista_contatos([
        {
            "usuario": usuario,
            "online": usuario in online
        }
        for usuario in repositorio_usuarios.listar_usuarios()
    ])


def enviar_evento(arquivo, evento):
    """
    Envia um evento JSON para o cliente.
    """

    dados = serializar(evento)

    arquivo.write(dados)
    arquivo.flush()


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

    def run(self):

        print(
            f"[NOVA CONEXÃO] "
            f"{self.endereco[0]}:{self.endereco[1]}"
        )

        try:

            while True:

                linha = self.arquivo.readline()

                if not linha:
                    break

                evento = desserializar(linha)

                print(
                    f"[RECEBIDO] "
                    f"{self.endereco}: {evento}"
                )

                self.processar_evento(evento)

        except ConnectionError:

            print(
                f"[DESCONECTADO] "
                f"{self.endereco}"
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
            resposta = servico_chat.registrar_usuario(
                evento.get("usuario"),
                evento.get("senha")
            )

            self.enviar(resposta)

            return

        if tipo == "login":
            usuario = evento.get("usuario")
            senha = evento.get("senha")
            resposta = servico_chat.autenticar_usuario(
                usuario,
                senha
            )

            if not resposta["sucesso"]:
                self.enviar(resposta)
                return

            with usuarios_online_lock:
                if usuario in usuarios_online:
                    resposta = {
                        "evento": "resposta_login",
                        "sucesso": False,
                        "mensagem": "Usuário já está conectado."
                    }
                else:
                    usuarios_online[usuario] = self
                    self.usuario = usuario

            self.enviar(resposta)

            if resposta["sucesso"]:
                self.enviar(criar_lista_contatos_atualizada())

                mensagens_offline = (
                    repositorio_mensagens.listar_e_remover(usuario)
                )

                if mensagens_offline:
                    self.enviar(criar_fila_offline(mensagens_offline))

            return

        if tipo == "mensagem":
            if self.usuario is None:
                self.enviar(
                    {
                        "evento": "erro",
                        "mensagem": "É necessário fazer login antes de enviar mensagens."
                    }
                )
                return

            destinatario = evento.get("destinatario")
            mensagem = criar_mensagem(
                self.usuario,
                destinatario,
                evento.get("timestamp"),
                evento.get("texto")
            )

            with usuarios_online_lock:
                cliente_destinatario = usuarios_online.get(destinatario)

            if cliente_destinatario is not None:
                cliente_destinatario.enviar(mensagem)
            else:
                repositorio_mensagens.adicionar(
                    destinatario,
                    mensagem
                )

            self.enviar(criar_entrega_mensagem(
                self.usuario,
                destinatario,
                evento.get("timestamp")
            ))
            return

        resposta = {
            "evento": "evento_recebido",
            "tipo": tipo
        }

        self.enviar(resposta)

    def enviar(self, evento):
        with self.envio_lock:
            enviar_evento(self.arquivo, evento)

    def fechar(self):

        if self.usuario is not None:
            with usuarios_online_lock:
                if usuarios_online.get(self.usuario) is self:
                    usuarios_online.pop(self.usuario)

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


