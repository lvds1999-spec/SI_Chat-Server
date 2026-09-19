import json
import os
import threading


ARQUIVO_MENSAGENS = "mensagens_offline.json"


class RepositorioMensagens:

    def __init__(self):
        self.arquivo = ARQUIVO_MENSAGENS
        self._lock = threading.Lock()
        self._criar_arquivo_se_nao_existir()

    def _criar_arquivo_se_nao_existir(self):
        if not os.path.exists(self.arquivo):
            with open(
                self.arquivo,
                "w",
                encoding="utf-8"
            ) as arquivo:
                json.dump({}, arquivo, ensure_ascii=False, indent=4)

    def _carregar(self):
        with open(
            self.arquivo,
            "r",
            encoding="utf-8"
        ) as arquivo:
            return json.load(arquivo)

    def _salvar(self, mensagens):
        with open(
            self.arquivo,
            "w",
            encoding="utf-8"
        ) as arquivo:
            json.dump(
                mensagens,
                arquivo,
                ensure_ascii=False,
                indent=4
            )

    def adicionar(self, destinatario, mensagem):
        with self._lock:
            mensagens = self._carregar()
            mensagens.setdefault(destinatario, []).append(mensagem)
            self._salvar(mensagens)

    def listar_e_remover(self, destinatario):
        with self._lock:
            mensagens = self._carregar()
            fila = mensagens.pop(destinatario, [])
            self._salvar(mensagens)
            return fila