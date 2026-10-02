import threading

from src.infraestrutura.persistencia.banco import conectar


class RepositorioContatos:

    def __init__(self):
        self._lock = threading.Lock()

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
            return cursor.rowcount == 1
