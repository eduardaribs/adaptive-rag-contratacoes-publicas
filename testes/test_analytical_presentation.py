import pytest

from src.analytical_presentation import renderizar_agrupamento


def resultado(grupos, **extras):
    return {
        "operacao": "contar",
        "campo": None,
        "agrupar_por": ["situacao_item"],
        "grupos": grupos,
        "total_grupos": len(grupos),
        "truncado": False,
        **extras,
    }


def test_tabela_preserva_grupos_e_contagens():
    tabela = renderizar_agrupamento(resultado([
        {"situacao_item": "Homologado", "valor": 8},
        {"situacao_item": "Fracassado", "valor": 9},
        {"situacao_item": "Deserto", "valor": 2},
    ]))
    assert tabela["colunas"] == ["Situação", "Quantidade"]
    assert tabela["linhas"] == [
        ["Homologado", "8"],
        ["Fracassado", "9"],
        ["Deserto", "2"],
    ]
    assert "| Homologado | 8 |" in tabela["markdown"]


def test_preserva_zero_e_distingue_ausencia():
    tabela = renderizar_agrupamento(resultado([
        {"situacao_item": "A", "valor": 0},
        {"situacao_item": "B", "valor": None, "completo": False},
    ]))
    assert tabela["linhas"] == [["A", "0"], ["B", "Não informado"]]
    assert tabela["notas"]


def test_preserva_precisao_decimal():
    tabela = renderizar_agrupamento(resultado(
        [{"situacao_item": "A", "valor": "1234.56789"}],
        operacao="media",
        campo="valor_total_estimado",
    ))
    assert tabela["linhas"][0][1] == "1234,56789"


def test_conteudo_nao_quebra_colunas():
    tabela = renderizar_agrupamento(resultado([
        {"situacao_item": "<A>|B\nC", "valor": 1},
    ]))
    assert tabela["linhas"][0][0] == "&lt;A&gt;&#124;B C"


def test_informa_truncamento():
    tabela = renderizar_agrupamento(resultado(
        [{"situacao_item": "A", "valor": 1}],
        total_grupos=5,
        truncado=True,
    ))
    assert "Exibidos 1 de 5 grupos." in tabela["markdown"]


@pytest.mark.parametrize("grupo", [
    {"valor": 1},
    {"situacao_item": "A"},
    {"situacao_item": "A", "valor": "NaN"},
    {"situacao_item": "A", "valor": "1.5"},
])
def test_rejeita_grupos_inconsistentes(grupo):
    with pytest.raises(ValueError):
        renderizar_agrupamento(resultado([grupo]))
