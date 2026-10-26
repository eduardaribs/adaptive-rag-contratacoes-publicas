import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.analytical_transport import decodificar_interpretacao
from src.analytical_interpreter import InterpretacaoAnalitica
from src.analytical_executor import executar_analitico


def resposta(operacao):
    return json.dumps({
        "tipo": "plano", "mensagem": "", "pedido_documental": None,
        "plano": {
            "fonte": "pca",
            "tarefas": [{
                "id": "m", "operacao": operacao,
                "campo": "valor_total_estimado",
                "filtros": [], "agrupar_por": [],
            }],
        },
    })


def test_media_geral_preservada_ate_o_calculo():
    interpretacao = InterpretacaoAnalitica.model_validate(
        decodificar_interpretacao(resposta("media"))
    )
    resultado = executar_analitico(interpretacao.plano, [
        {"valor_total_estimado": "10"},
        {"valor_total_estimado": "30"},
    ])
    medida = resultado["resultados"][0]
    assert Decimal(medida["valor"]) == Decimal("20")
    assert medida["total_registros"] == 2
    assert "grupos" not in medida


def test_nome_invalido_produz_um_erro_direto():
    with pytest.raises(ValidationError) as falha:
        decodificar_interpretacao(resposta("medir"))
    erros = falha.value.errors()
    assert len(erros) == 1
    assert erros[0]["type"] == "union_tag_invalid"
