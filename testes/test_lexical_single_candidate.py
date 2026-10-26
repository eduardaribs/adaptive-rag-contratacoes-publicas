import pytest
from rank_bm25 import BM25Okapi

from src.retrieval_lexical import buscar_contexto, tokenizar_contexto


def natureza(chunk):
    return "conversacional"


def test_candidato_unico_com_correspondencia_preserva_score_real():
    texto = "prazo entrega papel prazo entrega"
    pergunta = "prazo entrega"
    chunks = {"a": {"text": texto, "metadata": {}}}

    score = float(
        BM25Okapi([tokenizar_contexto(texto)])
        .get_scores(tokenizar_contexto(pergunta))[0]
    )
    assert score < 0

    resultado = buscar_contexto(
        pergunta, [{"chunk_id": "a"}], chunks, natureza,
    )
    assert len(resultado) == 1
    assert resultado[0]["chunk_id"] == "a"
    assert resultado[0]["bm25_score"] == pytest.approx(score)


def test_candidato_unico_sem_correspondencia_nao_e_retornado():
    resultado = buscar_contexto(
        "software",
        [{"chunk_id": "a"}],
        {"a": {"text": "papel caneta", "metadata": {}}},
        natureza,
    )
    assert resultado == []


def test_candidato_unico_respeita_limite_zero():
    resultado = buscar_contexto(
        "papel",
        [{"chunk_id": "a"}],
        {"a": {"text": "papel caneta", "metadata": {}}},
        natureza,
        fetch_k=0,
    )
    assert resultado == []
