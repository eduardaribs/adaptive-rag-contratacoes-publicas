from copy import deepcopy

from src.query_executor import executar_plano
from src.query_decomposition import extrair_pedido_documental
from app.pipeline_adapter import _preparar_entrada_geracao


PERGUNTA = (
    "Quantas contratações têm ano da compra 2026 "
    "e o que a Lei nº 14.133/2021 estabelece sobre o pregão?"
)
DOCUMENTAL = "o que a Lei nº 14.133/2021 estabelece sobre o pregão?"


def test_recuperacao_recebe_somente_pedido_documental():
    analise = {
        "query": PERGUNTA, "query_id": "q_teste",
        "routes": ["estruturada", "normativa"],
        "filters": {"ano": 2026},
    }
    original = deepcopy(analise)
    chamadas = []

    def recuperar(**kwargs):
        chamadas.append(kwargs)
        return {
            "query": kwargs["pergunta"],
            "query_id": "q_teste",
            "routes": ["normativa"], "evidences": [],
        }

    resultado = executar_plano(
        PERGUNTA,
        {
            "bases": ["estruturada", "normativa"],
            "estrategia": "combinada", "operacao": "contar",
            "filtros": {"ano_compra": 2026},
            "rotas_recuperacao": ["normativa"],
            "query_id": "q_teste",
        },
        base=[
            {"id_pncp": "1", "ano_compra": "2026", "fonte_original": "teste"},
            {"id_pncp": "2", "ano_compra": "2025", "fonte_original": "teste"},
        ],
        analise_pronta=analise,
        recuperador=recuperar, run_id="run_teste",
    )
    assert resultado["total"] == 1
    assert resultado["query"] == PERGUNTA
    assert resultado["hibrida"]["query_original"] == PERGUNTA
    assert chamadas[0]["pergunta"] == DOCUMENTAL
    assert chamadas[0]["analise_pronta"]["query"] == DOCUMENTAL
    assert chamadas[0]["analise_pronta"]["filters"] == {}
    assert chamadas[0]["run_id"] == "run_teste"
    assert analise == original

    entrada = _preparar_entrada_geracao(
        resultado["hibrida"], combinada=True
    )
    assert entrada["query"] == DOCUMENTAL


def test_nao_divide_perguntas_arbitrarias():
    assert extrair_pedido_documental(
        "Liste contratos de papel e canetas."
    ) is None
