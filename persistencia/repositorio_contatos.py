import json
from pathlib import Path
import threading

from persistencia.banco import conectar


ARQUIVO_CONTATOS = "contatos.json"


class RepositorioContatos:

    def __init__(self):
        self._lock = threading.Lock()
        self._migrar_json_se_necessario()

    def _migrar_json_se_necessario(self):
        caminho = Path(__file__).resolve().parent.parent / ARQUIVO_CONTATOS

        if not caminho.exists():
            return

        with self._lock, conectar() as conexao:
            quantidade = conexao.execute(
                "SELECT COUNT(*) FROM contatos"
            ).fetchone()[0]

            if quantidade != 0:
                return

            dados = json.loads(caminho.read_text(encoding="utf-8"))
            registros = [
                (usuario, contato)
                for usuario, contatos in dados.items()
                for contato in contatos
            ]
            conexao.executemany(
                "INSERT OR IGNORE INTO contatos (usuario, contato) VALUES (?, ?)",
                registros
            )

    def listar(self, usuario):
        with conectar() as conexao:
            linhas = conexao.execute(
                "SELECT contato FROM contatos WHERE usuario = ? ORDER BY contato",
                (usuario,)
            ).fetchall()
            return [linha["contato"] for linha in linhas]

    def adicionar(self, usuario, contato):
        with self._lock, conectar() as conexao:
            cursor = conexao.execute(
                "INSERT OR IGNORE INTO contatos (usuario, contato) VALUES (?, ?)",
                (usuario, contato)
            )
            return cursor.rowcount == 1

    def remover(self, usuario, contato):
        with self._lock, conectar() as conexao:
            cursor = conexao.execute(
                "DELETE FROM contatos WHERE usuario = ? AND contato = ?",
                (usuario, contato)
            )
            return cursor.rowcount == 1
