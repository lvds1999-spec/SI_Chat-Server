import sqlite3
from pathlib import Path


ARQUIVO_BANCO = Path(__file__).resolve().parent.parent / "chat.db"


def conectar():
    conexao = sqlite3.connect(ARQUIVO_BANCO, timeout=30)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar():
    with conectar() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mensagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                timestamp TEXT,
                texto TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente', 'entregue', 'lido'))
            );

            CREATE INDEX IF NOT EXISTS idx_mensagens_recipient_status
                ON mensagens (recipient, status);

            CREATE TABLE IF NOT EXISTS contatos (
                usuario TEXT NOT NULL,
                contato TEXT NOT NULL,
                PRIMARY KEY (usuario, contato),
                FOREIGN KEY (usuario) REFERENCES usuarios (usuario),
                FOREIGN KEY (contato) REFERENCES usuarios (usuario)
            );

            CREATE TABLE IF NOT EXISTS migracoes (
                nome TEXT PRIMARY KEY
            );
            """
        )
        _migrar_contatos_para_ids(conexao)


def _migrar_contatos_para_ids(conexao):
    colunas = {
        linha["name"]
        for linha in conexao.execute("PRAGMA table_info(contatos)")
    }
    if "usuario_id" in colunas:
        return

    conexao.execute("ALTER TABLE contatos RENAME TO contatos_legado")
    conexao.execute(
        """
        CREATE TABLE contatos (
            usuario_id INTEGER NOT NULL,
            contato_id INTEGER NOT NULL,
            PRIMARY KEY (usuario_id, contato_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (contato_id) REFERENCES usuarios (id)
        )
        """
    )
    conexao.execute(
        """
        INSERT OR IGNORE INTO contatos (usuario_id, contato_id)
        SELECT usuario.id, contato.id
        FROM contatos_legado AS legado
        JOIN usuarios AS usuario ON usuario.usuario = legado.usuario
        JOIN usuarios AS contato ON contato.usuario = legado.contato
        """
    )
    conexao.execute("DROP TABLE contatos_legado")


inicializar()
