
from copy import deepcopy

import pytest
from src.router import planejar_consulta


@pytest.mark.parametrize("ano", [2025, 2026])
@pytest.mark.parametrize("rotas", [
    ["agregada", "normativa"],
    ["normativa"],
    ["estruturada", "normativa"],
])
def test_contagem_com_documento_preserva_duas_tarefas(ano, rotas):
    analise = {
        "query_id": "q_combinada_rota",
        "routes": rotas,
        "filters": {},
        "is_refusal": False,
    }
    antes = deepcopy(analise)
    plano = planejar_consulta(
        f"Quantas contratações têm ano da compra {ano} "
        "e o que a Lei nº 14.133/2021 estabelece sobre o pregão?",
        analise=analise,
    )
    assert plano["estrategia"] == "combinada"
    assert plano["operacao"] == "contar"
    assert set(plano["bases"]) == {"estruturada", "normativa"}
    assert plano["rotas_recuperacao"] == ["normativa"]
    assert plano["filtros"]["ano_compra"] == ano
    assert "agregada" not in plano["bases"]
    assert analise == antes


@pytest.mark.parametrize("pergunta", [
    "Quantas modalidades de contratação a Lei nº 14.133/2021 estabelece?",
    "O que a Lei nº 14.133/2021 estabelece sobre o pregão?",
])
def test_pergunta_normativa_nao_vira_contagem_de_registros(pergunta):
    plano = planejar_consulta(
        pergunta,
        analise={
            "query_id": "q_normativa",
            "routes": ["normativa"],
            "filters": {},
            "is_refusal": False,
        },
    )
    assert plano["estrategia"] == "recuperacao_hibrida"
    assert plano["bases"] == ["normativa"]
