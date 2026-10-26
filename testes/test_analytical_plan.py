import pytest
from pydantic import ValidationError

from src.analytical_plan import PlanoAnalitico


def test_contagem_simples_nao_exige_resumo_completo():
    plano = PlanoAnalitico.model_validate({
        "fonte": "itens_pe",
        "tarefas": [{
            "id": "homologados",
            "operacao": "contar",
            "filtros": [{
                "campo": "situacao_item",
                "operador": "igual",
                "valor": "homologado",
            }],
        }],
    })
    assert len(plano.tarefas) == 1
    assert plano.tarefas[0].operacao == "contar"


def test_comparacao_e_percentual_com_resultados_calculados():
    plano = PlanoAnalitico.model_validate({
        "fonte": "itens_pe",
        "tarefas": [
            {"id": "total", "operacao": "contar"},
            {
                "id": "homologados",
                "operacao": "contar",
                "filtros": [{
                    "campo": "situacao_item",
                    "operador": "igual",
                    "valor": "homologado",
                }],
            },
        ],
        "comparacoes": [{
            "id": "participacao",
            "operacao": "percentual",
            "esquerda": "homologados",
            "direita": "total",
        }],
    })
    assert plano.comparacoes[0].direita == "total"


def test_soma_agrupada_e_formato_tabela():
    plano = PlanoAnalitico.model_validate({
        "fonte": "pca",
        "formato": "tabela",
        "tarefas": [{
            "id": "por_categoria",
            "operacao": "somar",
            "campo": "valor_total_estimado",
            "agrupar_por": ["categoria"],
        }],
    })
    assert plano.formato == "tabela"


@pytest.mark.parametrize("alteracao", [
    {"fonte": "arquivo_inventado"},
    {"codigo_python": "print('nao executar')"},
    {"tarefas": [{"id": "x", "operacao": "executar_codigo"}]},
    {"tarefas": [{"id": "x", "operacao": "somar", "campo": "fornecedor"}]},
    {"filtros": [{"campo": "cpf", "operador": "igual", "valor": "123"}]},
    {"tarefas": [{"id": "x", "operacao": "listar", "campos": ["inexistente"]}]},
    {"tarefas": [{"id": "x", "operacao": "listar", "campos": ["fornecedor"],
                  "limite": 100000}]},
    {"comparacoes": [{"id": "c", "operacao": "percentual",
                      "esquerda": "inexistente", "direita": "total"}]},
])
def test_rejeita_planos_inexecutaveis(alteracao):
    entrada = {
        "fonte": "itens_pe",
        "tarefas": [{"id": "total", "operacao": "contar"}],
        **alteracao,
    }
    with pytest.raises(ValidationError):
        PlanoAnalitico.model_validate(entrada)
