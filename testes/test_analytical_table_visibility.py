from copy import deepcopy

import pytest

from app.app import apresentar


def resultado(estrategia):
    markdown = (
        "| Situação | Quantidade |\n"
        "| --- | --- |\n"
        "| Homologado | 8 |"
    )
    return {
        "query": "Mostre uma tabela.",
        "answer": markdown + "\n\n[Fonte: calculo]",
        "run_id": "run_tabela",
        "query_id": "q_tabela",
        "executado": True,
        "estrategia": estrategia,
        "campos": ["Situação", "Quantidade"],
        "registros": [{"Situação": "Homologado", "Quantidade": "8"}],
        "tabelas_analiticas": [{
            "markdown": markdown,
            "colunas": ["Situação", "Quantidade"],
            "linhas": [["Homologado", "8"]],
        }],
        "resposta_completa": True,
    }


@pytest.mark.parametrize("estrategia", [
    "consulta_analitica", "combinada_analitica"
])
def test_oculta_painel_duplicado_sem_apagar_dados(estrategia):
    r = resultado(estrategia)
    antes = deepcopy(r)
    exibicao = apresentar(r)

    assert exibicao[0] == r["answer"]
    assert exibicao[1]["visible"] is False
    assert exibicao[1]["value"]["data"] == [["Homologado", "8"]]
    assert r == antes


def test_mantem_painel_quando_tabela_nao_esta_na_resposta():
    r = resultado("consulta_analitica")
    r["answer"] = "Confira os registros abaixo."
    assert apresentar(r)[1]["visible"] is True


def test_preserva_tabela_de_listagem_estruturada():
    r = resultado("consulta_estruturada")
    r["operacao"] = "listar"
    r["pagina"] = 1
    r["total_paginas"] = 1
    assert apresentar(r)[1]["visible"] is True
