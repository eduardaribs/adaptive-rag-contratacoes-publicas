import pytest

from src import rerank
from src.schema import SourceEvidence


@pytest.fixture
def backend_local(monkeypatch):
    monkeypatch.setattr(rerank, "RERANK_ENABLED", True)
    monkeypatch.setattr(rerank, "MAX_CANDIDATES", 3)
    monkeypatch.setenv("RERANK_BACKEND", "local")


def candidatos():
    return [
        {
            "id": str(i),
            "text": f"Trecho {i}",
            "metadata": {"source_file": "teste.pdf"},
        }
        for i in range(4)
    ]


def instalar_modelo(monkeypatch, scores):
    class Modelo:
        def predict(self, pares, **kwargs):
            assert len(pares) == 3
            return scores

    monkeypatch.setattr(
        rerank, "_carregar_modelo", lambda *args: Modelo()
    )


def test_ordena_preserva_empates_metadados_e_excedentes(
    monkeypatch, backend_local
):
    instalar_modelo(monkeypatch, [1.0, 1.0, 3.0])
    entrada = candidatos()

    saida = rerank.executar_rerank("Pergunta", entrada)

    assert [doc["id"] for doc, _ in saida] == ["2", "0", "1", "3"]
    assert [score for _, score in saida] == [3.0, 1.0, 1.0, None]
    for doc, _ in saida:
        assert doc is entrada[int(doc["id"])]

    evento = rerank.ultimo_resultado()
    assert evento["applied"] is True
    assert evento["candidates_scored"] == 3
    assert evento["candidates_preserved_unscored"] == 1


@pytest.mark.parametrize("scores", [
    [1.0],
    [1.0, float("nan"), 2.0],
    [1.0, float("inf"), 2.0],
])
def test_scores_invalidos_preservam_rrf(
    monkeypatch, backend_local, scores
):
    instalar_modelo(monkeypatch, scores)
    entrada = candidatos()

    assert rerank.executar_rerank("Pergunta", entrada) == [
        (doc, None) for doc in entrada
    ]
    assert rerank.ultimo_resultado()["status"] == "failed_fallback_rrf"
    assert rerank.ultimo_resultado()["applied"] is False


def test_falha_de_carregamento_preserva_rrf(
    monkeypatch, backend_local
):
    def falhar(*args):
        raise OSError("Modelo indisponível")

    monkeypatch.setattr(rerank, "_carregar_modelo", falhar)
    entrada = candidatos()

    assert rerank.executar_rerank("Pergunta", entrada) == [
        (doc, None) for doc in entrada
    ]
    assert rerank.ultimo_resultado()["applied"] is False


@pytest.mark.parametrize("score", [3.2, -6.0, None])
def test_schema_preserva_score(score):
    evidencia = SourceEvidence(
        chunk_id="teste",
        text="Trecho sintético",
        rerank_score=score,
    )
    assert evidencia.model_dump()["rerank_score"] == score
