from copy import deepcopy
import pytest

from src.normative_selection import cobrir_definicao


def ambiente(assunto="pregão"):
    ranking = [
        {"chunk_id": "aplicacao", "rrf_score": 0.04},
        {"chunk_id": "modalidade", "rrf_score": 0.03},
        {"chunk_id": "agente", "rrf_score": 0.02},
        {"chunk_id": "definicao", "rrf_score": 0.01},
    ]
    chunks = {
        "aplicacao": {"text": "Regras de aplicação."},
        "modalidade": {"text": "Modalidades disponíveis."},
        "agente": {"text": "Atuação do agente."},
        "definicao": {"text": f"{assunto}: modalidade de licitação."},
    }
    return ranking, chunks


@pytest.mark.parametrize("assunto", [
    "pregão", "concorrência", "leilão", "diálogo competitivo",
])
def test_reserva_definicao_pelo_conteudo(assunto):
    ranking, chunks = ambiente(assunto)
    original = deepcopy((ranking, chunks))

    resultado = cobrir_definicao(
        f"O que a lei estabelece sobre {assunto}?",
        ranking, chunks, ["normativa"], 3,
    )

    assert [item["chunk_id"] for item in resultado[:3]] == [
        "aplicacao", "modalidade", "definicao",
    ]
    assert sorted(item["chunk_id"] for item in resultado) == sorted(
        item["chunk_id"] for item in ranking
    )
    assert (ranking, chunks) == original
    assert next(
        item["rrf_score"] for item in resultado
        if item["chunk_id"] == "definicao"
    ) == 0.01


@pytest.mark.parametrize("pergunta,rotas,top_k", [
    ("O que o artigo 29 estabelece sobre pregão?", ["normativa"], 3),
    ("Quais são as exceções ao pregão?", ["normativa"], 3),
    ("O que a lei estabelece sobre pregão?", ["normativa"], 1),
    ("O que a lei estabelece sobre pregão?",
     ["normativa", "conversacional"], 3),
    ("O que a lei estabelece sobre pregão?", ["conversacional"], 3),
])
def test_pedidos_especificos_e_outras_rotas_preservam_ranking(
    pergunta, rotas, top_k,
):
    ranking, chunks = ambiente()
    assert cobrir_definicao(
        pergunta, ranking, chunks, rotas, top_k,
    ) == ranking


def test_nao_acrescenta_definicao_fora_dos_candidatos():
    ranking, chunks = ambiente()
    ranking = ranking[:3]
    assert cobrir_definicao(
        "O que a lei estabelece sobre pregão?",
        ranking, chunks, ["normativa"], 3,
    ) == ranking


def test_sem_definicao_preserva_ranking():
    ranking, chunks = ambiente()
    chunks["definicao"]["text"] = "Apenas uma referência ao pregão."
    assert cobrir_definicao(
        "O que a lei estabelece sobre pregão?",
        ranking, chunks, ["normativa"], 3,
    ) == ranking
