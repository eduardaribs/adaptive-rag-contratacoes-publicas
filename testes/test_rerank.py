import logging

import pytest

from src import rerank


@pytest.fixture
def candidatos():
    return [
        {
            "id": f"doc{i}",
            "text": f"Texto {i}",
            "metadata": {"natureza": "normativa"},
            "rrf_score_original": 0.03 / (i + 1),
        }
        for i in range(30)
    ]


@pytest.mark.parametrize("habilitado", [False, True])
def test_fallback_preserva_ordem_metadados_e_todos_candidatos(
    monkeypatch, candidatos, habilitado
):
    monkeypatch.setattr(rerank, "RERANK_ENABLED", habilitado)
    monkeypatch.setattr(rerank, "TOP_K", 3)
    monkeypatch.setattr(rerank, "MAX_CANDIDATES", 20)

    resultado = rerank.executar_rerank("Pergunta", candidatos)

    assert len(resultado) == 30
    assert [doc for doc, _ in resultado] == candidatos
    assert all(doc is original for (doc, _), original in zip(
        resultado, candidatos
    ))
    assert all(score is None for _, score in resultado)


def test_lista_vazia():
    assert rerank.executar_rerank("Pergunta", []) == []


def test_ativacao_sem_integracao_nao_registra_sucesso(
    monkeypatch, caplog, candidatos
):
    monkeypatch.setattr(rerank, "RERANK_ENABLED", True)

    with caplog.at_level(logging.WARNING, logger=rerank.__name__):
        rerank.executar_rerank("Pergunta", candidatos)

    assert "not_implemented_fallback_rrf" in caplog.text
    assert "'applied': False" in caplog.text
    assert "'status': 'success'" not in caplog.text


def test_fallback_nao_altera_lista_recebida(monkeypatch, candidatos):
    monkeypatch.setattr(rerank, "RERANK_ENABLED", True)
    ordem = [doc["id"] for doc in candidatos]

    rerank.executar_rerank("Pergunta", candidatos)

    assert [doc["id"] for doc in candidatos] == ordem
