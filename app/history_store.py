"""Histórico persistente de resultados apresentados pela interface."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3


def caminho_historico():
    return Path(os.getenv(
        "HISTORY_PATH", "data/history/consultas.sqlite3"
    ))


def _conectar():
    caminho = caminho_historico()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(str(caminho), timeout=10)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS consultas (
            run_id TEXT PRIMARY KEY,
            query_id TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            pergunta TEXT NOT NULL,
            resultado TEXT NOT NULL
        )
    """)
    return conexao


def salvar_consulta(resultado):
    """Salva uma execução sem sobrescrever uma execução já registrada."""
    if not isinstance(resultado, dict):
        raise ValueError("Resultado deve ser um dicionário.")

    for campo in ("run_id", "query_id", "query", "answer"):
        valor = resultado.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"Campo obrigatório inválido: {campo}")

    # Serializa antes de abrir a transação; não modifica o resultado.
    conteudo = json.dumps(
        resultado, ensure_ascii=False, allow_nan=False
    )
    conexao = _conectar()
    try:
        with conexao:
            cursor = conexao.execute(
                """INSERT OR IGNORE INTO consultas
                (run_id, query_id, criado_em, pergunta, resultado)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    resultado["run_id"],
                    resultado["query_id"],
                    datetime.now(timezone.utc).isoformat(),
                    resultado["query"],
                    conteudo,
                ),
            )
            return cursor.rowcount == 1
    finally:
        conexao.close()


def listar_consultas(limite=50):
    """Retorna as execuções mais recentes, sem carregar suas evidências."""
    if not isinstance(limite, int) or not 1 <= limite <= 500:
        raise ValueError("Limite deve estar entre 1 e 500.")
    if not caminho_historico().is_file():
        return []

    conexao = _conectar()
    try:
        linhas = conexao.execute(
            """SELECT run_id, query_id, criado_em, pergunta
            FROM consultas ORDER BY criado_em DESC, rowid DESC LIMIT ?""",
            (limite,),
        ).fetchall()
        return [
            dict(zip(
                ("run_id", "query_id", "criado_em", "pergunta"), linha
            ))
            for linha in linhas
        ]
    finally:
        conexao.close()


def carregar_consulta(run_id):
    """Recupera o resultado salvo; não chama o pipeline."""
    if not caminho_historico().is_file():
        return None

    conexao = _conectar()
    try:
        linha = conexao.execute(
            "SELECT resultado FROM consultas WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return json.loads(linha[0]) if linha else None
    finally:
        conexao.close()
