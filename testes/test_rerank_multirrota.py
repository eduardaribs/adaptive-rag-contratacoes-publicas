import pytest

from src import rerank, retrieve


@pytest.mark.parametrize("habilitado", [False, True])
def test_fallback_preserva_rota_apos_limite_antigo(
    monkeypatch, habilitado
):
    monkeypatch.setattr(rerank, "RERANK_ENABLED", habilitado)
    monkeypatch.setattr(rerank, "MAX_CANDIDATES", 20)
    monkeypatch.setattr(rerank, "TOP_K", 3)

    candidatos = [
        {
            "id": f"lei_{i}",
            "text": f"Trecho normativo {i}",
            "metadata": {
                "natureza": "normativa",
                "sensitivity": "publico",
            },
            "rrf_score_original": 1 / (60 + i),
        }
        for i in range(1, 26)
    ]
    candidatos.append({
        "id": "registro_pncp",
        "text": "Registro estruturado associado.",
        "metadata": {
            "natureza": "estruturada",
            "sensitivity": "publico",
        },
        "rrf_score_original": 1 / 100,
    })

    retorno = rerank.executar_rerank("Pergunta", candidatos)

    ranking = [
        {
            "chunk_id": documento["id"],
            "rrf_score": documento["rrf_score_original"],
            "rerank_score": score,
        }
        for documento, score in retorno
    ]
    chunks_por_id = {
        documento["id"]: {
            "text": documento["text"],
            "metadata": documento["metadata"],
        }
        for documento in candidatos
    }

    selecionados = retrieve.selecionar_resultados_multirrota(
        ranking,
        chunks_por_id,
        ["normativa", "estruturada"],
        top_k=3,
    )

    assert len(retorno) == 26
    assert len(selecionados) == 3
    assert [item["chunk_id"] for item in selecionados] == [
        "lei_1", "lei_2", "registro_pncp"
    ]
    assert all(item["rerank_score"] is None for item in selecionados)
    assert {
        retrieve.identificar_natureza(
            chunks_por_id[item["chunk_id"]]
        )
        for item in selecionados
    } == {"normativa", "estruturada"}
