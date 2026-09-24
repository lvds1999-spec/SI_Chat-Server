import json
import os
from pathlib import Path
import threading

from argon2.low_level import Type, hash_secret_raw

from persistencia.banco import conectar


ARQUIVO_USUARIOS = "usuarios.json"
SALT_TAMANHO = 16
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 4
HASH_TAMANHO = 32


class RepositorioUsuarios:

    def __init__(self):
        self._lock = threading.Lock()
        self._migrar_senhas_legadas()
        self._migrar_json_se_necessario()

    def _hash_senha(self, senha, salt):
        return hash_secret_raw(
            senha.encode("utf-8"),
            salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=HASH_TAMANHO,
            type=Type.ID,
        )

    def _migrar_senhas_legadas(self):
        with self._lock, conectar() as conexao:
            colunas = {
                linha["name"]
                for linha in conexao.execute("PRAGMA table_info(usuarios)")
            }
            if "senha" not in colunas:
                return

            linhas = conexao.execute(
                "SELECT usuario, senha FROM usuarios "
                "WHERE senha_hash IS NULL AND senha IS NOT NULL"
            ).fetchall()
            for linha in linhas:
                salt = os.urandom(SALT_TAMANHO)
                senha_hash = self._hash_senha(linha["senha"], salt)
                conexao.execute(
                    "UPDATE usuarios SET senha_hash = ?, salt = ? "
                    "WHERE usuario = ?",
                    (senha_hash, salt, linha["usuario"])
                )

            try:
                conexao.execute("ALTER TABLE usuarios DROP COLUMN senha")
            except Exception:
                # Bancos SQLite antigos mantem a coluna legada, mas ela
                # deixa de ser usada depois da migracao.
                pass

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
            for usuario, dados_usuario in dados.items():
                senha = dados_usuario["senha"]
                salt = os.urandom(SALT_TAMANHO)
                conexao.execute(
                    "INSERT OR IGNORE INTO usuarios "
                    "(usuario, senha_hash, salt) VALUES (?, ?, ?)",
                    (usuario, self._hash_senha(senha, salt), salt)
                )

    def usuario_existe(self, usuario):
        with conectar() as conexao:
            return conexao.execute(
                "SELECT 1 FROM usuarios WHERE usuario = ?",
                (usuario,)
            ).fetchone() is not None

    def cadastrar(self, usuario, senha, chave_publica=None):
        if not isinstance(usuario, str) or not isinstance(senha, str):
            return False
        salt = os.urandom(SALT_TAMANHO)
        senha_hash = self._hash_senha(senha, salt)
        with self._lock, conectar() as conexao:
            try:
                conexao.execute(
                    "INSERT INTO usuarios "
                    "(usuario, senha_hash, salt, chave_publica) "
                    "VALUES (?, ?, ?, ?)",
                    (usuario, senha_hash, salt, chave_publica)
                )
            except Exception:
                return False

            return True

    def autenticar(self, usuario, senha):
        if not isinstance(usuario, str) or not isinstance(senha, str):
            return False
        with conectar() as conexao:
            linha = conexao.execute(
                "SELECT senha_hash, salt FROM usuarios WHERE usuario = ?",
                (usuario,)
            ).fetchone()

        if linha is None or linha["senha_hash"] is None:
            return False

        senha_hash = self._hash_senha(senha, bytes(linha["salt"]))
        return senha_hash == bytes(linha["senha_hash"])

    def obter_chave_publica(self, usuario):
        with conectar() as conexao:
            linha = conexao.execute(
                "SELECT chave_publica FROM usuarios WHERE usuario = ?",
                (usuario,)
            ).fetchone()
            return None if linha is None else linha["chave_publica"]

    def atualizar_chave_publica(self, usuario, chave_publica):
        with self._lock, conectar() as conexao:
            cursor = conexao.execute(
                "UPDATE usuarios SET chave_publica = ? WHERE usuario = ?",
                (chave_publica, usuario)
            )
            return cursor.rowcount == 1

    def listar_usuarios(self):
        with conectar() as conexao:
            linhas = conexao.execute(
                "SELECT usuario FROM usuarios ORDER BY usuario"
            ).fetchall()
            return [linha["usuario"] for linha in linhas]
