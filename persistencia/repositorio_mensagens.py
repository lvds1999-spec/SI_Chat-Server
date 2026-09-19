import json
from pathlib import Path
import threading

from persistencia.banco import conectar


ARQUIVO_MENSAGENS = "mensagens_offline.json"


class RepositorioMensagens:

    def __init__(self):
        self._lock = threading.Lock()
        self._migrar_json_se_necessario()

    def _migrar_json_se_necessario(self):
        caminho = Path(__file__).resolve().parent.parent / ARQUIVO_MENSAGENS

        if not caminho.exists():
            return

        with self._lock, conectar() as conexao:
            quantidade = conexao.execute(
                "SELECT COUNT(*) FROM mensagens"
            ).fetchone()[0]

            if quantidade != 0:
                return

            dados = json.loads(caminho.read_text(encoding="utf-8"))
            registros = []
            for destinatario, mensagens in dados.items():
                for mensagem in mensagens:
                    registros.append((
                        mensagem.get("remetente", ""),
                        destinatario,
                        mensagem.get("timestamp"),
                        mensagem.get("texto", ""),
                        "pendente"
                    ))

            conexao.executemany(
                """
                INSERT INTO mensagens
                    (sender, recipient, timestamp, texto, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                registros
            )

    def adicionar(self, destinatario, mensagem, status="pendente"):
        with self._lock, conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO mensagens
                    (sender, recipient, timestamp, texto, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    mensagem.get("remetente", ""),
                    destinatario,
                    mensagem.get("timestamp"),
                    mensagem.get("texto", ""),
                    status
                )
            )
            return cursor.lastrowid

    def listar_e_remover(self, destinatario):
        with self._lock, conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT id, sender, recipient, timestamp, texto, status
                FROM mensagens
                WHERE recipient = ? AND status = 'pendente'
                ORDER BY id
                """,
                (destinatario,)
            ).fetchall()

            ids = [linha["id"] for linha in linhas]
            if ids:
                marcadores = ",".join("?" for _ in ids)
                conexao.execute(
                    f"UPDATE mensagens SET status = 'entregue' "
                    f"WHERE id IN ({marcadores})",
                    ids
                )

            return [
                {
                    "evento": "mensagem",
                    "id": linha["id"],
                    "remetente": linha["sender"],
                    "destinatario": linha["recipient"],
                    "timestamp": linha["timestamp"],
                    "texto": linha["texto"],
                    "status": "entregue"
                }
                for linha in linhas
            ]

    def marcar_lida(self, mensagem_id):
        with self._lock, conectar() as conexao:
            conexao.execute(
                "UPDATE mensagens SET status = 'lido' WHERE id = ?",
                (mensagem_id,)
            )
