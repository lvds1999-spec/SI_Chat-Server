import sqlite3
from pathlib import Path


ARQUIVO_BANCO = Path(__file__).resolve().parent.parent / "chat.db"


def conectar():
    conexao = sqlite3.connect(ARQUIVO_BANCO, timeout=30)
    conexao.row_factory = sqlite3.Row
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
            """
        )


inicializar()
