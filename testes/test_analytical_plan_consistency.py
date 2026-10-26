import pytest
from pydantic import ValidationError

from src.analytical_plan import PlanoAnalitico


def filtro(valor):
    return {"campo": "situacao_item", "operador": "igual", "valor": valor}


def test_bloqueia_grupos_diferentes_em_filtros_globais():
    with pytest.raises(ValidationError, match="contraditórios"):
        PlanoAnalitico.model_validate({
            "fonte": "itens_pe",
            "filtros": [filtro("homologado"), filtro("fracassado")],
            "tarefas": [{"id": "n", "operacao": "contar"}],
        })


def test_bloqueia_contradicao_entre_filtro_global_e_tarefa():
    with pytest.raises(ValidationError, match="contraditórios"):
        PlanoAnalitico.model_validate({
            "fonte": "itens_pe",
            "filtros": [filtro("homologado")],
            "tarefas": [{
                "id": "n", "operacao": "contar",
                "filtros": [filtro("fracassado")],
            }],
        })


def test_comparacao_usa_grupos_separados():
    plano = PlanoAnalitico.model_validate({
        "fonte": "itens_pe",
        "tarefas": [
            {"id": "h", "operacao": "contar", "filtros": [filtro("homologado")]},
            {"id": "f", "operacao": "contar", "filtros": [filtro("fracassado")]},
        ],
        "comparacoes": [{
            "id": "d", "operacao": "diferenca",
            "esquerda": "h", "direita": "f",
        }],
    })
    assert len(plano.tarefas) == 2


def test_bloqueia_contagem_comparada_com_quantidade_fisica():
    with pytest.raises(ValidationError, match="grandezas incompatíveis"):
        PlanoAnalitico.model_validate({
            "fonte": "itens_pe",
            "tarefas": [
                {"id": "n", "operacao": "contar"},
                {"id": "q", "operacao": "somar",
                 "campo": "quantidade_homologada"},
            ],
            "comparacoes": [{
                "id": "d", "operacao": "diferenca",
                "esquerda": "n", "direita": "q",
            }],
        })


def test_normaliza_campos_opcionais_vazios():
    plano = PlanoAnalitico.model_validate({
        "fonte": "itens_pe",
        "tarefas": [{
            "id": "n", "operacao": "contar",
            "campo": "", "ordenar_por": "",
        }],
    })
    assert plano.tarefas[0].campo is None
    assert plano.tarefas[0].ordenar_por is None
