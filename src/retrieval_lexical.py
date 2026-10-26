"""Busca lexical sobre candidatos elegíveis, com foco no objeto PNCP."""

import json
import re
import unicodedata

from nltk.stem.snowball import PortugueseStemmer
from rank_bm25 import BM25Okapi

_STEMMER_PORTUGUES = PortugueseStemmer()


PALAVRAS_GERAIS = set("""
a o as os um uma de do da dos das em no na nos nas
e ou para por com sobre ao aos que qual quais como
existe existem contratacao contratacoes contrato contratos
lei estabelece numero segundo informe
""".split())


def tokenizar_contexto(texto):
    """Preserva acentos durante o stemming em português."""
    texto = unicodedata.normalize("NFC", str(texto).casefold())
    saida = []
    for token in re.findall(r"[a-zà-öø-ÿ]+", texto):
        simples = "".join(
            c for c in unicodedata.normalize("NFD", token)
            if not unicodedata.combining(c)
        )
        if simples in PALAVRAS_GERAIS:
            continue
        if simples.startswith("vidrac"):
            raiz = "vidrac"
        elif simples.startswith("elevador"):
            raiz = "elevador"
        else:
            raiz = _STEMMER_PORTUGUES.stem(token)
        saida.append("".join(
            c for c in unicodedata.normalize("NFD", raiz)
            if not unicodedata.combining(c)
        ))
    return saida


def texto_contexto(chunk, identificar_natureza):
    texto = chunk.get("text", "")
    metadata = chunk.get("metadata", {})

    if identificar_natureza(chunk) == "estruturada":
        objeto = metadata.get("objeto") or metadata.get("objetoCompra")

        if not objeto:
            try:
                registro = json.loads(texto)
            except (json.JSONDecodeError, TypeError):
                registro = {}

            if isinstance(registro, dict):
                objeto = registro.get("objetoCompra") or registro.get("objeto")

        if objeto:
            return str(objeto)

    return str(texto)


def buscar_contexto(
    pergunta,
    candidatos,
    chunks_por_id,
    identificar_natureza,
    fetch_k=50,
):
    """Calcula BM25 apenas sobre os candidatos previamente filtrados.

    Não modifica chunks, não grava índices e não usa IDs de respostas
    esperadas. Scores não positivos são omitidos, exceto no conjunto de um único candidato com termos compartilhados. A pontuação original é preservada.
    """
    if fetch_k <= 0 or not candidatos:
        return []

    tokens_pergunta = tokenizar_contexto(pergunta)
    if not tokens_pergunta:
        return []

    corpus = [
        tokenizar_contexto(
            texto_contexto(
                chunks_por_id[item["chunk_id"]],
                identificar_natureza,
            )
        )
        for item in candidatos
    ]

    if not any(corpus):
        return []

    scores = BM25Okapi(corpus).get_scores(tokens_pergunta)
    posicoes = sorted(
        range(len(scores)),
        key=lambda posicao: float(scores[posicao]),
        reverse=True,
    )

    return [
        {
            "chunk_id": candidatos[posicao]["chunk_id"],
            "bm25_score": float(scores[posicao]),
        }
        for posicao in posicoes
        if (
            float(scores[posicao]) > 0
            or (
                len(candidatos) == 1
                and bool(set(tokens_pergunta) & set(corpus[posicao]))
            )
        )
    ][:fetch_k]
