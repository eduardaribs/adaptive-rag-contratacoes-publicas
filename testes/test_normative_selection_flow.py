import json
import pytest

from src import retrieve


@pytest.mark.parametrize("pergunta,aplicada", [
    ("O que a lei estabelece sobre pregão?", True),
    ("Quais são as exceções ao pregão?", False),
])
def test_cobertura_normativa_no_recuperador_e_log(
    monkeypatch, tmp_path, pergunta, aplicada
):
    monkeypatch.setattr(retrieve.obs, "PASTA_LOGS", tmp_path)
    monkeypatch.setattr(retrieve.rerank, "RERANK_ENABLED", False)

    textos = {
        "aplicacao": "Regras e exceções de aplicação do pregão.",
        "modalidade": "O pregão é uma modalidade.",
        "agente": "O agente será designado pregoeiro.",
        "definicao": "Pregão: modalidade para bens e serviços comuns.",
    }
    chunks = [
        {
            "text": texto,
            "metadata": {
                "chunk_id": identificador,
                "source_file": "lei.html",
                "natureza": "normativa",
                "base_id": "base_normativa",
                "doc_type": "lei",
                "sensitivity": "publico",
            },
        }
        for identificador, texto in textos.items()
    ]
    ids = list(textos)
    por_id = {
        c["metadata"]["chunk_id"]: c for c in chunks
    }

    monkeypatch.setattr(
        retrieve, "carregar_artefatos",
        lambda: (chunks, por_id, ids, object(), object()),
    )
    monkeypatch.setattr(
        retrieve, "busca_densa",
        lambda **kwargs: [
            {"chunk_id": identificador, "dense_distance": float(i)}
            for i, identificador in enumerate(ids)
        ],
    )

    import src.retrieval_lexical as lexical
    monkeypatch.setattr(
        lexical, "buscar_contexto",
        lambda **kwargs: [
            {"chunk_id": identificador, "bm25_score": float(10 - i)}
            for i, identificador in enumerate(ids)
        ],
    )

    resultado = retrieve.recuperar_evidencias(
        pergunta=pergunta,
        top_k=3,
        fetch_k=50,
        client=object(),
        analise_pronta={
            "query": pergunta,
            "query_id": "q_cobertura",
            "routes": ["normativa"],
            "filters": {},
            "is_refusal": False,
            "refusal_reason": None,
        },
        run_id="run_cobertura",
    )

    esperados = (
        ["aplicacao", "modalidade", "definicao"]
        if aplicada else
        ["aplicacao", "modalidade", "agente"]
    )
    assert [
        e["chunk_id"] for e in resultado["evidences"]
    ] == esperados

    eventos = [
        json.loads(linha)
        for caminho in tmp_path.glob("pipeline-*.jsonl")
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    fusoes = [e for e in eventos if e["stage"] == "fusao_rrf"]
    assert len(fusoes) == 1

    evento = fusoes[0]
    assert evento["status"] == "ok"
    assert evento["query_id"] == "q_cobertura"
    assert evento["run_id"] == "run_cobertura"

    saida = evento["output"]
    assert saida["cobertura_definicao_aplicada"] is aplicada
    assert saida["top_ids_antes_cobertura"] == [
        "aplicacao", "modalidade", "agente"
    ]
    assert saida["top_ids_apos_cobertura"] == esperados
    assert saida["rerank_applied"] is False
    assert saida["politica_selecao"] == (
        "cobertura_definicao_normativa_v1"
    )
    assert textos["definicao"] not in json.dumps(
        saida, ensure_ascii=False
    )
