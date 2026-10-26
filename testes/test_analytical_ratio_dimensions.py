from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.analytical_plan import PlanoAnalitico
from src.analytical_executor import executar_analitico


def plano(operacao="razao", contar_campo=False):
    return {
        "fonte": "pca",
        "tarefas": [
            {
                "id": "soma",
                "operacao": "somar",
                "campo": "valor_total_estimado",
            },
            {
                "id": "quantidade",
                "operacao": "contar",
                "campo": "valor_total_estimado" if contar_campo else None,
            },
        ],
        "comparacoes": [{
            "id": "resultado",
            "operacao": operacao,
            "esquerda": "soma",
            "direita": "quantidade",
        }],
    }


def test_razao_admite_valor_por_registro():
    validado = PlanoAnalitico.model_validate(plano())
    resultado = executar_analitico(validado, [
        {"valor_total_estimado": "10.00"},
        {"valor_total_estimado": "30.00"},
    ])
    comparacao = resultado["comparacoes"][0]
    assert Decimal(comparacao["valor"]) == Decimal("20")
    assert comparacao["completo"] is True


@pytest.mark.parametrize("operacao", ["diferenca", "percentual"])
def test_nao_libera_diferenca_ou_percentual_entre_grandezas(operacao):
    with pytest.raises(ValidationError, match="grandezas incompatíveis"):
        PlanoAnalitico.model_validate(plano(operacao))


def test_media_por_razao_exclui_ausentes_do_denominador():
    resultado = executar_analitico(plano(contar_campo=True), [
        {"valor_total_estimado": "10.00"},
        {"valor_total_estimado": None},
        {"valor_total_estimado": "30.00"},
    ])
    assert resultado["resultados"][1]["valor"] == 2
    assert Decimal(resultado["comparacoes"][0]["valor"]) == Decimal("20")
    # A existência de valor ausente continua registrada.
    assert resultado["resultados"][0]["valores_ausentes"] == 1


def test_divisao_por_zero_continua_sem_resultado_numerico():
    resultado = executar_analitico(plano(), [])
    comparacao = resultado["comparacoes"][0]
    assert comparacao["valor"] is None
    assert comparacao["motivo"]
