import json
from pathlib import Path
import threading


ARQUIVO_CONTATOS = Path(__file__).resolve().parents[1] / "contatos.json"


class RepositorioContatos:

    def __init__(self):
        self.arquivo = ARQUIVO_CONTATOS
        self._lock = threading.Lock()
        self._criar_arquivo_se_nao_existir()

    def _criar_arquivo_se_nao_existir(self):
        if not self.arquivo.exists():
            with self.arquivo.open("w", encoding="utf-8") as arquivo:
                json.dump({}, arquivo, ensure_ascii=False, indent=4)

    def _carregar(self):
        with self.arquivo.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    def _salvar(self, contatos):
        with self.arquivo.open("w", encoding="utf-8") as arquivo:
            json.dump(contatos, arquivo, ensure_ascii=False, indent=4)

    def listar(self, usuario):
        with self._lock:
            contatos = self._carregar()
            return list(contatos.get(usuario, []))

    def adicionar(self, usuario, contato):
        with self._lock:
            contatos = self._carregar()
            lista = contatos.setdefault(usuario, [])
            if contato in lista:
                return False
            lista.append(contato)
            self._salvar(contatos)
            return True

    def remover(self, usuario, contato):
        with self._lock:
            contatos = self._carregar()
            lista = contatos.get(usuario, [])
            if contato not in lista:
                return False
            lista.remove(contato)
            self._salvar(contatos)
            return True
