from src.retrieve import selecionar_resultados_multirrota


def criar_dados():
    chunks = {
        "e1": {
            "metadata": {
                "natureza": "estruturada",
            }
        },
        "e2": {
            "metadata": {
                "natureza": "estruturada",
            }
        },
        "n1": {
            "metadata": {
                "natureza": "normativa",
            }
        },
        "n2": {
            "metadata": {
                "natureza": "normativa",
            }
        },
    }

    ranking = [
        {"chunk_id": "e1", "rrf_score": 0.90},
        {"chunk_id": "e2", "rrf_score": 0.80},
        {"chunk_id": "n1", "rrf_score": 0.70},
        {"chunk_id": "n2", "rrf_score": 0.60},
    ]

    return chunks, ranking


def test_uma_rota_preserva_ranking():
    chunks, ranking = criar_dados()

    resultado = selecionar_resultados_multirrota(
        ranking,
        chunks,
        ["estruturada"],
        top_k=2,
    )

    assert [item["chunk_id"] for item in resultado] == [
        "e1",
        "e2",
    ]


def test_duas_rotas_sao_preservadas():
    chunks, ranking = criar_dados()

    resultado = selecionar_resultados_multirrota(
        ranking,
        chunks,
        ["normativa", "estruturada"],
        top_k=3,
    )

    ids = [item["chunk_id"] for item in resultado]

    assert "e1" in ids
    assert "n1" in ids
    assert len(ids) == 3


def test_rota_sem_resultado_nao_causa_erro():
    chunks, ranking = criar_dados()

    resultado = selecionar_resultados_multirrota(
        ranking,
        chunks,
        ["conversacional", "estruturada"],
        top_k=2,
    )

    assert len(resultado) == 2
    assert resultado[0]["chunk_id"] == "e1"


def test_respeita_top_k_global():
    chunks, ranking = criar_dados()

    resultado = selecionar_resultados_multirrota(
        ranking,
        chunks,
        ["normativa", "estruturada"],
        top_k=2,
    )

    naturezas = {
        chunks[item["chunk_id"]]["metadata"]["natureza"]
        for item in resultado
    }

    assert len(resultado) == 2
    assert naturezas == {
        "normativa",
        "estruturada",
    }


def test_top_k_zero_retorna_lista_vazia():
    chunks, ranking = criar_dados()

    resultado = selecionar_resultados_multirrota(
        ranking,
        chunks,
        ["normativa", "estruturada"],
        top_k=0,
    )

    assert resultado == []
