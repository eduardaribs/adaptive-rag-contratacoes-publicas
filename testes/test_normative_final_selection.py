import json
from types import SimpleNamespace

import pytest

from src.normative_selection import cobrir_selecao_definicao


def evidencias():
    return [
        SimpleNamespace(chunk_id="a", text="Aplicação.", natureza="normativa"),
        SimpleNamespace(chunk_id="b", text="Modalidades.", natureza="normativa"),
        SimpleNamespace(
            chunk_id="d", text="Pregão: modalidade para bens comuns.",
            natureza="normativa",
        ),
    ]


def test_preserva_definicao_recuperada():
    resultado = cobrir_selecao_definicao(
        "O que a lei estabelece sobre o pregão?",
        json.dumps({"chunk_ids": ["a", "b"]}),
        evidencias(), ["normativa"],
    )
    assert json.loads(resultado)["chunk_ids"] == ["a", "b", "d"]


def test_pergunta_especifica_nao_recebe_definicao():
    original = json.dumps({"chunk_ids": ["a", "b"]})
    assert cobrir_selecao_definicao(
        "O que o artigo 29 estabelece sobre pregão?",
        original, evidencias(), ["normativa"],
    ) == original


def test_id_inventado_continua_bloqueado():
    with pytest.raises(ValueError, match="não foi recuperado"):
        cobrir_selecao_definicao(
            "O que a lei estabelece sobre pregão?",
            json.dumps({"chunk_ids": ["inventado"]}),
            evidencias(), ["normativa"],
        )


def test_selecao_unica_recebe_definicao():
    resultado = cobrir_selecao_definicao(
        "O que a lei estabelece sobre pregão?",
        json.dumps({"chunk_ids": ["a"]}),
        evidencias(), ["normativa"],
    )
    assert json.loads(resultado)["chunk_ids"] == ["a", "d"]


def test_limite_de_cinco_preservado():
    fontes = [
        SimpleNamespace(
            chunk_id=f"x{i}", text="Regra específica.", natureza="normativa"
        )
        for i in range(5)
    ] + evidencias()[2:]
    resultado = cobrir_selecao_definicao(
        "O que a lei estabelece sobre pregão?",
        json.dumps({"chunk_ids": [f"x{i}" for i in range(5)]}),
        fontes, ["normativa"],
    )
    assert json.loads(resultado)["chunk_ids"] == [
        "x0", "x1", "x2", "x3", "d"
    ]


def test_definicao_ja_selecionada_preserva_saida():
    original = json.dumps({"chunk_ids": ["d", "a"]})
    assert cobrir_selecao_definicao(
        "O que a lei estabelece sobre pregão?",
        original, evidencias(), ["normativa"],
    ) == original
