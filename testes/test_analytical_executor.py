from decimal import Decimal

import pytest

from src.analytical_executor import executar_analitico


@pytest.fixture
def linhas():
    return [
        {"situacao_item": "homologado", "valor_total_homologado": "0.1",
         "fornecedor": "Empresa A", "numero_item": "1"},
        {"situacao_item": "homologado", "valor_total_homologado": "0.2",
         "fornecedor": "Empresa B", "numero_item": "2"},
        {"situacao_item": "fracassado", "valor_total_homologado": None,
         "fornecedor": "", "numero_item": "3"},
        {"situacao_item": "deserto", "valor_total_homologado": None,
         "fornecedor": "", "numero_item": "4"},
    ]


def executar(linhas, tarefas, **extras):
    return executar_analitico({
        "fonte": "itens_pe", "tarefas": tarefas, **extras,
    }, linhas)


def test_contagem_filtrada(linhas):
    r = executar(linhas, [{
        "id": "n", "operacao": "contar",
        "filtros": [{"campo": "situacao_item", "operador": "igual",
                     "valor": "HOMOLOGADO"}],
    }])
    assert r["resultados"][0]["valor"] == 2


@pytest.mark.parametrize("operacao,esperado", [
    ("somar", "0.3"), ("media", "0.15"),
    ("minimo", "0.1"), ("maximo", "0.2"),
])
def test_medidas_decimais_exatas(linhas, operacao, esperado):
    r = executar(linhas, [{
        "id": "medida", "operacao": operacao,
        "campo": "valor_total_homologado",
        "filtros": [{"campo": "situacao_item", "operador": "igual",
                     "valor": "homologado"}],
    }])
    medida = r["resultados"][0]
    assert Decimal(medida["valor"]) == Decimal(esperado)
    assert medida["completo"] is True


def test_ausentes_nao_viram_zero_silenciosamente(linhas):
    r = executar(linhas, [{
        "id": "soma", "operacao": "somar",
        "campo": "valor_total_homologado",
    }])
    medida = r["resultados"][0]
    assert medida["valor"] == "0.3"
    assert medida["valores_ausentes"] == 2
    assert medida["completo"] is False


def test_todos_ausentes_nao_produzem_soma_zero(linhas):
    r = executar(linhas[2:], [{
        "id": "soma", "operacao": "somar",
        "campo": "valor_total_homologado",
    }])
    assert r["resultados"][0]["valor"] is None


def test_agrupamento_calcula_todos_os_grupos(linhas):
    r = executar(linhas, [{
        "id": "situacoes", "operacao": "contar",
        "agrupar_por": ["situacao_item"],
    }])
    grupos = {
        g["situacao_item"]: g["valor"]
        for g in r["resultados"][0]["grupos"]
    }
    assert grupos == {"homologado": 2, "fracassado": 1, "deserto": 1}


def test_limite_de_listagem_nao_limita_calculos(linhas):
    r = executar(linhas, [
        {"id": "lista", "operacao": "listar",
         "campos": ["numero_item"], "limite": 1},
        {"id": "total", "operacao": "contar"},
    ])
    assert len(r["resultados"][0]["registros"]) == 1
    assert r["resultados"][0]["total_registros"] == 4
    assert r["resultados"][1]["valor"] == 4


def test_percentual_e_diferenca(linhas):
    tarefas = [
        {"id": "total", "operacao": "contar"},
        {"id": "h", "operacao": "contar",
         "filtros": [{"campo": "situacao_item", "operador": "igual",
                      "valor": "homologado"}]},
    ]
    r = executar(linhas, tarefas, comparacoes=[
        {"id": "percentual", "operacao": "percentual",
         "esquerda": "h", "direita": "total"},
        {"id": "diferenca", "operacao": "diferenca",
         "esquerda": "total", "direita": "h"},
    ])
    assert Decimal(r["comparacoes"][0]["valor"]) == Decimal("50")
    assert Decimal(r["comparacoes"][1]["valor"]) == Decimal("2")


def test_divisao_por_zero_e_explicita(linhas):
    r = executar(linhas, [
        {"id": "total", "operacao": "contar"},
        {"id": "zero", "operacao": "contar",
         "filtros": [{"campo": "situacao_item", "operador": "igual",
                      "valor": "inexistente"}]},
    ], comparacoes=[{
        "id": "razao", "operacao": "razao",
        "esquerda": "total", "direita": "zero",
    }])
    assert r["comparacoes"][0]["valor"] is None
    assert r["comparacoes"][0]["motivo"] == "Denominador igual a zero."


def test_filtros_globais_e_da_tarefa_sao_combinados(linhas):
    r = executar(linhas, [{
        "id": "n", "operacao": "contar",
        "filtros": [{"campo": "valor_total_homologado",
                     "operador": "maior_igual", "valor": "0.2"}],
    }], filtros=[{
        "campo": "situacao_item", "operador": "igual", "valor": "homologado",
    }])
    assert r["resultados"][0]["valor"] == 1


def test_listagem_ordenada_numericamente(linhas):
    r = executar(linhas, [{
        "id": "lista", "operacao": "listar",
        "campos": ["numero_item"],
        "ordenar_por": "numero_item", "ordem": "decrescente",
        "limite": 2,
    }])
    assert r["resultados"][0]["registros"] == [
        {"numero_item": "4"}, {"numero_item": "3"},
    ]


def test_nao_altera_registros_recebidos(linhas):
    import copy
    antes = copy.deepcopy(linhas)
    executar(linhas, [{"id": "n", "operacao": "contar"}])
    assert linhas == antes


def test_bloqueia_plano_com_pendencias(linhas):
    with pytest.raises(ValueError, match="pendências"):
        executar(
            linhas, [{"id": "n", "operacao": "contar"}],
            pendencias=["Definir a base solicitada."],
        )


def test_rejeita_valor_nao_finito(linhas):
    linhas[0]["valor_total_homologado"] = "NaN"
    with pytest.raises(ValueError, match="não finito"):
        executar(linhas, [{
            "id": "soma", "operacao": "somar",
            "campo": "valor_total_homologado",
        }])


def test_contagem_distinta_exclui_ausentes(linhas):
    r = executar(linhas, [{
        "id": "fornecedores", "operacao": "contar",
        "campo": "fornecedor", "distintos": True,
    }])
    assert r["resultados"][0]["valor"] == 2
    assert r["resultados"][0]["valores_ausentes"] == 2
