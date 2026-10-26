"""Persistência local do feedback fornecido pela interface."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any


CAMINHO_FEEDBACK_PADRAO = "data/feedback/feedback.jsonl"

AVALIACOES_VALIDAS = {
    "Útil": "util",
    "Não útil": "nao_util",
    "util": "util",
    "nao_util": "nao_util",
}


def _caminho_feedback() -> Path:
    """Retorna o caminho configurado para o histórico de feedback."""
    return Path(
        os.getenv(
            "FEEDBACK_PATH",
            CAMINHO_FEEDBACK_PADRAO,
        )
    )


def _extrair_identificador(
    status: str,
    nome: str,
) -> str | None:
    """
    Extrai identificadores apresentados no status da interface.

    Remove a marcação Markdown para reconhecer corretamente textos
    como: **Run ID:** abc123.
    """
    texto_limpo = (
        str(status or "")
        .replace("*", "")
        .replace("`", "")
    )

    padrao = rf"{re.escape(nome)}\s*:\s*([\w-]+)"

    encontrado = re.search(
        padrao,
        texto_limpo,
        flags=re.IGNORECASE,
    )

    if encontrado:
        return encontrado.group(1)

    return None


def _extrair_fontes(
    evidencias: Any,
) -> list[str]:
    """Obtém fontes únicas das evidências exibidas."""
    if not isinstance(evidencias, list):
        return []

    fontes = []

    for evidencia in evidencias:
        if not isinstance(evidencia, dict):
            continue

        metadata = evidencia.get("metadata", {})

        if not isinstance(metadata, dict):
            metadata = {}

        fonte = (
            evidencia.get("fonte")
            or evidencia.get("source_file")
            or metadata.get("source_file")
        )

        if fonte and str(fonte) not in fontes:
            fontes.append(str(fonte))

    return fontes


def _normalizar_rota(rota: Any) -> Any:
    """
    Preserva o formato da rota apresentado pela interface.

    A compatibilidade com os registros anteriores exige que uma rota
    textual continue sendo salva como string.
    """
    if isinstance(rota, str):
        return rota.strip()

    if isinstance(rota, list):
        return rota

    return rota


def registrar_feedback(
    pergunta: str,
    avaliacao: str,
    comentario: str,
    rota: Any,
    evidencias: Any,
    status: str,
) -> str:
    """Acrescenta um feedback ao JSONL sem apagar registros anteriores."""
    pergunta = str(pergunta or "").strip()

    if not pergunta:
        return (
            "⚠️ Faça uma consulta antes de registrar o feedback."
        )

    avaliacao_normalizada = AVALIACOES_VALIDAS.get(
        str(avaliacao or "").strip()
    )

    if not avaliacao_normalizada:
        return (
            "⚠️ Selecione **Útil** ou **Não útil** "
            "antes de enviar."
        )

    query_id = _extrair_identificador(
        status,
        "Query ID",
    )

    run_id = _extrair_identificador(
        status,
        "Run ID",
    )

    if not query_id or not run_id:
        return (
            "⚠️ Não foi possível identificar a consulta. "
            "Execute novamente a pergunta antes de enviar "
            "o feedback."
        )

    registro = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "pergunta": pergunta,
        "avaliacao": avaliacao_normalizada,
        "comentario": str(comentario or "").strip(),
        "query_id": query_id,
        "run_id": run_id,
        "rota": _normalizar_rota(rota),
        "fontes": _extrair_fontes(evidencias),
    }

    caminho = _caminho_feedback()

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with caminho.open(
        "a",
        encoding="utf-8",
    ) as arquivo_saida:
        arquivo_saida.write(
            json.dumps(
                registro,
                ensure_ascii=False,
            )
            + "\n"
        )

    return (
        "✅ Feedback salvo com sucesso. "
        f"Avaliação: **{avaliacao_normalizada}**."
    )


def registrar_util(
    pergunta,
    comentario,
    rota,
    evidencias,
    status,
):
    """Mantém compatibilidade com a interface anterior."""
    return registrar_feedback(
        pergunta=pergunta,
        avaliacao="util",
        comentario=comentario,
        rota=rota,
        evidencias=evidencias,
        status=status,
    )


def registrar_nao_util(
    pergunta,
    comentario,
    rota,
    evidencias,
    status,
):
    """Mantém compatibilidade com a interface anterior."""
    return registrar_feedback(
        pergunta=pergunta,
        avaliacao="nao_util",
        comentario=comentario,
        rota=rota,
        evidencias=evidencias,
        status=status,
    )
