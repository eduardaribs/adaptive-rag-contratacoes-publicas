
import pytest
from src.router import planejar_consulta
from src.query_decomposition import extrair_pedido_documental


def analise(rotas):
    return {
        "query_id": "q_intencao_documental",
        "routes": rotas,
        "filters": {"uf": "RJ"},
        "is_refusal": False,
    }


@pytest.mark.parametrize("rotas", [
    ["normativa", "estruturada"],
    ["normativa"],
    ["conversacional", "estruturada"],
    ["agregada", "normativa", "estruturada"],
])
def test_p01_nao_executa_tarefa_documental_nao_solicitada(rotas):
    pergunta = (
        "Quais contratações de pregão eletrônico foram "
        "publicadas no RJ em março de 2026?"
    )
    plano = planejar_consulta(pergunta, analise=analise(rotas))
    assert plano["estrategia"] == "consulta_estruturada"
    assert plano["operacao"] == "listar"
    assert plano["bases"] == ["estruturada"]
    assert plano["rotas_recuperacao"] == []
    assert plano["filtros"]["data_inicial"] == "2026-03-01"
    assert plano["filtros"]["modalidade_id"] == 6


@pytest.mark.parametrize("pergunta, rota", [
    (
        "Quantas contratações existem e o que a legislação diz sobre MEI?",
        "normativa",
    ),
    (
        "Liste as contratações e explique a regra.",
        "normativa",
    ),
    (
        "Liste as contratações e informe o que foi discutido nas atas.",
        "conversacional",
    ),
])
def test_segundo_pedido_documental_permanece_combinado(pergunta, rota):
    plano = planejar_consulta(
        pergunta, analise=analise(["estruturada", rota])
    )
    assert plano["estrategia"] == "combinada"
    assert set(plano["bases"]) == {"estruturada", rota}
    assert extrair_pedido_documental(pergunta)


@pytest.mark.parametrize("pergunta", [
    "Liste as contratações de 2026, mostre apenas objeto e município.",
    "Quais contratações de pregão eletrônico foram publicadas no RJ?",
])
def test_campos_e_modalidade_nao_criam_pedido_documental(pergunta):
    assert extrair_pedido_documental(pergunta) is None


def test_pergunta_exclusivamente_normativa_permanece_documental():
    plano = planejar_consulta(
        "O que a Lei nº 14.133/2021 estabelece sobre o pregão?",
        analise=analise(["normativa"]),
    )
    assert plano["estrategia"] == "recuperacao_hibrida"
    assert plano["bases"] == ["normativa"]


@pytest.mark.parametrize("referencia", [
    "Decreto nº 11.462/2023",
    "Resolução nº 100/2024",
    "Portaria nº 50/2022",
])
def test_outros_atos_normativos_preservam_combinada(referencia):
    pergunta = (
        "Quantas contratações têm ano da compra 2026 "
        f"e o que o {referencia} estabelece sobre o pregão?"
    )
    plano = planejar_consulta(
        pergunta, analise=analise(["estruturada", "normativa"])
    )
    assert extrair_pedido_documental(pergunta)
    assert plano["estrategia"] == "combinada"
    assert plano["filtros"]["ano_compra"] == 2026
    assert plano["necessita_esclarecimento"] is False
