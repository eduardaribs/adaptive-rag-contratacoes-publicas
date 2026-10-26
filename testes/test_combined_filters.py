from copy import deepcopy

from src.query_executor import (
    executar_plano,
    _montar_analise_recuperacao,
)


def test_combinada_nao_aplica_ano_da_compra_na_lei():
    pergunta = (
        "Quantas contratações têm ano da compra 2026 "
        "e o que a Lei nº 14.133 estabelece sobre o pregão?"
    )
    base = [
        {
            "id_pncp": "1",
            "ano_compra": "2026",
            "fonte_original": "teste.json",
        },
        {
            "id_pncp": "2",
            "ano_compra": "2025",
            "fonte_original": "teste.json",
        },
    ]
    analise = {
        "query": pergunta,
        "query_id": "q_filtros",
        "routes": ["estruturada", "normativa"],
        "filters": {"ano": 2026, "uf": "RJ"},
        "is_refusal": False,
    }
    original = deepcopy(analise)
    chamadas = []

    def recuperar(**kwargs):
        chamadas.append(kwargs)
        assert kwargs["analise_pronta"]["filters"] == {}
        assert kwargs["analise_pronta"]["routes"] == ["normativa"]
        assert kwargs["analise_pronta"]["query_id"] == "q_filtros"
        assert kwargs["run_id"] == "run_filtros"
        return {
            "query_id": "q_filtros",
            "routes": ["normativa"],
            "evidences": [{"chunk_id": "lei_pregao"}],
        }

    resultado = executar_plano(
        pergunta,
        {
            "bases": ["estruturada", "normativa"],
            "estrategia": "combinada",
            "operacao": "contar",
            "filtros": {"ano_compra": 2026},
            "rotas_recuperacao": ["normativa"],
            "query_id": "q_filtros",
        },
        base=base,
        analise_pronta=analise,
        recuperador=recuperar,
        run_id="run_filtros",
    )

    assert len(chamadas) == 1
    assert resultado["total"] == 1
    assert resultado["estruturada"]["filtros_aplicados"] == {
        "ano_compra": 2026
    }
    assert resultado["evidences"] == [{"chunk_id": "lei_pregao"}]
    assert resultado["query_id"] == "q_filtros"
    assert resultado["run_id"] == "run_filtros"
    assert analise == original


def test_preserva_filtros_documentais_explicitos():
    plano = {
        "estrategia": "combinada",
        "bases": ["estruturada", "conversacional"],
        "rotas_recuperacao": ["conversacional"],
        "filtros_recuperacao": {"ano": 2025, "orgao": "EBSERH"},
    }
    analise = {
        "routes": ["estruturada", "conversacional"],
        "filters": {"ano": 2026, "uf": "RJ"},
    }

    resultado = _montar_analise_recuperacao(plano, analise)

    assert resultado["filters"] == {"ano": 2025, "orgao": "EBSERH"}
    assert analise["filters"] == {"ano": 2026, "uf": "RJ"}


def test_consulta_documental_comum_preserva_filtros():
    plano = {
        "estrategia": "recuperacao_hibrida",
        "bases": ["normativa"],
    }
    analise = {
        "routes": ["normativa"],
        "filters": {"ano": 2021},
    }

    resultado = _montar_analise_recuperacao(plano, analise)

    assert resultado["filters"] == {"ano": 2021}


def test_normativa_preserva_criterios_que_nao_sao_da_contratacao():
    resultado = _montar_analise_recuperacao(
        {
            "estrategia": "combinada",
            "rotas_recuperacao": ["normativa"],
        },
        {
            "routes": ["estruturada", "normativa"],
            "filters": {"ano": 2026, "tema": "pregão"},
        },
    )

    assert resultado["filters"] == {"tema": "pregão"}
