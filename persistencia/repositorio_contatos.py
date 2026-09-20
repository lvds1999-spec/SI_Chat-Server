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

        with self._lock, conectar() as conexao:
            migracao_realizada = conexao.execute(
                "SELECT 1 FROM migracoes WHERE nome = ?",
                ("contatos_json",)
            ).fetchone()

            if migracao_realizada:
                return

            quantidade = conexao.execute(
                "SELECT COUNT(*) FROM contatos"
            ).fetchone()[0]

            if quantidade == 0 and caminho.exists():
                dados = json.loads(caminho.read_text(encoding="utf-8"))
                registros = [
                    (usuario_id[0], contato_id[0])
                    for usuario, contatos in dados.items()
                    for contato in contatos
                    for usuario_id in conexao.execute(
                        "SELECT id FROM usuarios WHERE usuario = ?",
                        (usuario,)
                    )
                    for contato_id in conexao.execute(
                        "SELECT id FROM usuarios WHERE usuario = ?",
                        (contato,)
                    )
                ]
                conexao.executemany(
                    "INSERT OR IGNORE INTO contatos (usuario_id, contato_id) VALUES (?, ?)",
                    registros
                )

            conexao.execute(
                "INSERT INTO migracoes (nome) VALUES (?)",
                ("contatos_json",)
            )

    def listar(self, usuario):
        with conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT contato.usuario
                FROM contatos
                JOIN usuarios AS usuario ON usuario.id = contatos.usuario_id
                JOIN usuarios AS contato ON contato.id = contatos.contato_id
                WHERE usuario.usuario = ?
                ORDER BY contato.usuario
                """,
                (usuario,)
            ).fetchall()
            return [linha["usuario"] for linha in linhas]

    def _salvar_json(self, conexao):
        if not (Path(__file__).resolve().parent.parent / ARQUIVO_CONTATOS).exists():
            return

        linhas = conexao.execute(
            """
            SELECT usuario.usuario AS usuario, contato.usuario AS contato
            FROM contatos
            JOIN usuarios AS usuario ON usuario.id = contatos.usuario_id
            JOIN usuarios AS contato ON contato.id = contatos.contato_id
            ORDER BY usuario.usuario, contato.usuario
            """
        ).fetchall()
        dados = {}
        for linha in linhas:
            dados.setdefault(linha["usuario"], []).append(linha["contato"])

        caminho = Path(__file__).resolve().parent.parent / ARQUIVO_CONTATOS
        caminho.write_text(
            json.dumps(dados, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8"
        )

    def adicionar(self, usuario, contato):
        with self._lock, conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT OR IGNORE INTO contatos (usuario_id, contato_id)
                SELECT usuario.id, contato.id
                FROM usuarios AS usuario, usuarios AS contato
                WHERE usuario.usuario = ? AND contato.usuario = ?
                """,
                (usuario, contato)
            )
            if cursor.rowcount == 1:
                self._salvar_json(conexao)
            return cursor.rowcount == 1

    def remover(self, usuario, contato):
        with self._lock, conectar() as conexao:
            cursor = conexao.execute(
                                """
                                DELETE FROM contatos
                                WHERE usuario_id = (SELECT id FROM usuarios WHERE usuario = ?)
                                    AND contato_id = (SELECT id FROM usuarios WHERE usuario = ?)
                                """,
                (usuario, contato)
            )
            if cursor.rowcount == 1:
                self._salvar_json(conexao)
            return cursor.rowcount == 1
