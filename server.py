import socket
import threading

from Protocolo.Rede.protocolo import (
    desserializar,
    serializar
)


HOST = "0.0.0.0"
PORTA = 8000


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

        if tipo == "teste":

            resposta = {
                "evento": "resposta_teste",
                "mensagem": "Servidor recebeu o evento."
            }

            enviar_evento(
                self.arquivo,
                resposta
            )

        else:

            resposta = {
                "evento": "evento_recebido",
                "tipo": tipo
            }

            enviar_evento(
                self.arquivo,
                resposta
            )

    def fechar(self):

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