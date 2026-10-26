import json

from src.analytical_transport import decodificar_interpretacao
from src.analytical_interpreter import InterpretacaoAnalitica
from src.analytical_executor import executar_analitico


def executar_tarefa(tarefa):
    interpretacao = InterpretacaoAnalitica.model_validate(
        decodificar_interpretacao(json.dumps({
            "tipo": "plano",
            "mensagem": "",
            "pedido_documental": None,
            "plano": {
                "fonte": "itens_pe",
                "tarefas": [tarefa],
                "formato": "tabela",
            },
        }))
    )
    return executar_analitico(interpretacao.plano, [
        {"situacao_item": "homologado"},
        {"situacao_item": "homologado"},
        {"situacao_item": "fracassado"},
    ])["resultados"][0]


def test_contagem_por_grupo_preservada_ate_o_executor():
    resultado = executar_tarefa({
        "id": "grupos",
        "operacao": "contar",
        "agrupar_por": ["situacao_item"],
    })
    grupos = {
        grupo["situacao_item"]: grupo["valor"]
        for grupo in resultado["grupos"]
    }
    assert grupos == {"homologado": 2, "fracassado": 1}
    assert "valor" not in resultado


def test_distintos_tem_significado_diferente_de_agrupamento():
    resultado = executar_tarefa({
        "id": "distintos",
        "operacao": "contar_distintos",
        "campo": "situacao_item",
    })
    assert resultado["valor"] == 2
    assert "grupos" not in resultado
