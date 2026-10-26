from copy import deepcopy

from app.pipeline_adapter import _preparar_entrada_geracao


def recuperacao():
    return {
        "query": (
            "Quantas contratações têm ano da compra 2026 "
            "e o que a Lei nº 14.133 estabelece sobre o pregão?"
        ),
        "query_id": "q_escopo",
        "routes": ["normativa"],
        "filters": {},
        "is_refusal": False,
        "evidences": [
            {"chunk_id": "lei_29", "text": "Trecho sobre pregão."}
        ],
    }


def test_combinada_delimita_geracao_sem_alterar_contexto():
    original = recuperacao()
    copia = deepcopy(original)

    entrada = _preparar_entrada_geracao(
        original, combinada=True
    )

    assert original == copia
    assert entrada["query_id"] == original["query_id"]
    assert entrada["evidences"] == original["evidences"]
    assert entrada["routes"] == original["routes"]
    assert entrada["filters"] == original["filters"]
    assert entrada["query"] == (
        "o que a Lei nº 14.133 estabelece sobre o pregão?"
    )
    assert "2026" not in entrada["query"]
    assert "Quantas contratações" in original["query"]


def test_documental_preserva_pergunta_e_nao_compartilha_mutacoes():
    original = recuperacao()
    entrada = _preparar_entrada_geracao(
        original, combinada=False
    )

    assert entrada == original
    entrada["evidences"].clear()
    assert original["evidences"]
