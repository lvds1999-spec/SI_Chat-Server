import json
from pathlib import Path
import threading

from persistencia.banco import conectar


ARQUIVO_USUARIOS = "usuarios.json"


class RepositorioUsuarios:

    def __init__(self):
        self._lock = threading.Lock()
        self._migrar_json_se_necessario()

    def _migrar_json_se_necessario(self):
        caminho = Path(__file__).resolve().parent.parent / ARQUIVO_USUARIOS

        if not caminho.exists():
            return

        with self._lock, conectar() as conexao:
            quantidade = conexao.execute(
                "SELECT COUNT(*) FROM usuarios"
            ).fetchone()[0]

            if quantidade != 0:
                return

            dados = json.loads(caminho.read_text(encoding="utf-8"))
            conexao.executemany(
                "INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES (?, ?)",
                [(usuario, dados_usuario["senha"])
                 for usuario, dados_usuario in dados.items()]
            )

    def usuario_existe(self, usuario):
        with conectar() as conexao:
            return conexao.execute(
                "SELECT 1 FROM usuarios WHERE usuario = ?",
                (usuario,)
            ).fetchone() is not None

    def cadastrar(self, usuario, senha):
        with self._lock, conectar() as conexao:
            try:
                conexao.execute(
                    "INSERT INTO usuarios (usuario, senha) VALUES (?, ?)",
                    (usuario, senha)
                )
            except Exception:
                return False

            return True

    def autenticar(self, usuario, senha):
        with conectar() as conexao:
            return conexao.execute(
                "SELECT 1 FROM usuarios WHERE usuario = ? AND senha = ?",
                (usuario, senha)
            ).fetchone() is not None

    def listar_usuarios(self):
        with conectar() as conexao:
            linhas = conexao.execute(
                "SELECT usuario FROM usuarios ORDER BY usuario"
            ).fetchall()
            return [linha["usuario"] for linha in linhas]
