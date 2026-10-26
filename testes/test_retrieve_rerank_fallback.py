import json

import pytest

from src import retrieve


@pytest.mark.parametrize("habilitado", [False, True])
def test_recuperador_preserva_multirrota_e_registra_fallback(
    monkeypatch, tmp_path, habilitado
):
    monkeypatch.setattr(retrieve.obs, "PASTA_LOGS", tmp_path)
    monkeypatch.setattr(
        retrieve.rerank, "RERANK_ENABLED", habilitado
    )
    monkeypatch.setattr(retrieve.rerank, "TOP_K", 3)
    monkeypatch.setattr(retrieve.rerank, "MAX_CANDIDATES", 20)

    chunks = [
        {
            "chunk_id": f"lei_{i}",
            "text": f"Trecho normativo {i}.",
            "metadata": {
                "chunk_id": f"lei_{i}",
                "natureza": "normativa",
                "base_id": "base_normativa",
                "source_file": "lei.html",
                "doc_type": "lei",
                "sensitivity": "publico",
            },
        }
        for i in range(1, 26)
    ]
    chunks.append({
        "chunk_id": "comunicacao_1",
        "text": "Comunicação sintética sobre o pedido.",
        "metadata": {
            "chunk_id": "comunicacao_1",
            "natureza": "conversacional",
            "base_id": "base_conversacional",
            "source_file": "comunicacao.txt",
            "doc_type": "ata_reuniao",
            "sensitivity": "publico",
        },
    })

    ids = [c["chunk_id"] for c in chunks]
    por_id = {c["chunk_id"]: c for c in chunks}

    analise = {
        "query": "Explique a regra e a comunicação.",
        "query_id": "q_fallback_offline",
        "routes": ["normativa", "conversacional"],
        "filters": {},
        "is_refusal": False,
        "refusal_reason": None,
        "justification": "Duas naturezas para teste offline.",
        "router_fallback": False,
    }

    monkeypatch.setattr(
        retrieve,
        "analisar_consulta",
        lambda pergunta, client, run_id=None: analise,
    )
    monkeypatch.setattr(
        retrieve,
        "carregar_artefatos",
        lambda: (chunks, por_id, ids, object(), object()),
    )
    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [
            {"chunk_id": identificador, "dense_distance": float(i)}
            for i, identificador in enumerate(ids)
        ],
    )
    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [
            {"chunk_id": identificador, "bm25_score": float(100 - i)}
            for i, identificador in enumerate(ids)
        ],
    )

    resultado = retrieve.recuperar_evidencias(
        pergunta=analise["query"],
        top_k=3,
        fetch_k=50,
        client=object(),
        run_id="run_fallback_offline",
    )

    assert resultado["stage"] == "fusao_rrf"
    assert resultado["query_id"] == "q_fallback_offline"
    assert len(resultado["evidences"]) == 3
    assert {
        evidencia["natureza"]
        for evidencia in resultado["evidences"]
    } == {"normativa", "conversacional"}
    assert "comunicacao_1" in {
        e["chunk_id"] for e in resultado["evidences"]
    }
    assert all(
        e.get("rerank_score") is None
        for e in resultado["evidences"]
    )

    eventos = [
        json.loads(linha)
        for caminho in tmp_path.glob("pipeline-*.jsonl")
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    fusoes = [e for e in eventos if e["stage"] == "fusao_rrf"]
    assert len(fusoes) == 1

    evento = fusoes[0]
    assert evento["run_id"] == "run_fallback_offline"
    assert evento["query_id"] == "q_fallback_offline"
    assert evento["status"] == "ok"
    assert evento["output"]["rrf_candidates"] == 26
    assert evento["output"]["returned"] == 3
    assert evento["output"]["rerank_enabled"] is habilitado
    assert evento["output"]["rerank_applied"] is False
    assert evento["output"]["rerank_status"] == (
        "not_implemented_fallback_rrf"
        if habilitado else "disabled_fallback_rrf"
    )
