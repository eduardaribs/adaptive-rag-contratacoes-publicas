import json
from types import SimpleNamespace

import pytest

from src.normative_query import reconhecer_pedido_normativo
from src.normative_selection import (
    cobrir_definicao,
    cobrir_selecao_definicao,
)
from src.grounded_quotes import preparar_selecao_extrativa


@pytest.mark.parametrize("pergunta, esperado", [
    ("O que a Lei nº 14.133/2021 estabelece sobre o pregão?", "pregao"),
    ("Explique as regras sobre pregão na Lei nº 14.133/2021.", "pregao"),
    ("Explique as regras sobre concorrência na lei.", "concorrencia"),
    ("O que o artigo 29 estabelece sobre pregão?", None),
    ("Informe a data de publicação da lei.", None),
])
def test_reconhecimento(pergunta, esperado):
    pedido = reconhecer_pedido_normativo(pergunta)
    assert (pedido.group(1).strip() if pedido else None) == esperado


def test_reformulacao_cobre_e_recorta_definicao_recuperada():
    pergunta = "Explique as regras sobre pregão na Lei nº 14.133/2021."
    evidencias = [
        SimpleNamespace(
            chunk_id="regra",
            natureza="normativa",
            text="Art. 29. Aplicação do pregão. Parágrafo único. Exceções.",
        ),
        SimpleNamespace(
            chunk_id="vigencia",
            natureza="normativa",
            text="Art. 194. Vigência da lei.",
        ),
        SimpleNamespace(
            chunk_id="outra",
            natureza="normativa",
            text="Art. 100. Outra disposição.",
        ),
        SimpleNamespace(
            chunk_id="definicao",
            natureza="normativa",
            text=(
                "Art. 6º XL - leilão: maior lance; "
                "XLI - pregão: bens e serviços comuns; "
                "XLII - diálogo competitivo: diálogos;"
            ),
        ),
    ]
    ranking = [
        {"chunk_id": e.chunk_id, "rrf_score": 1 / (i + 1)}
        for i, e in enumerate(evidencias)
    ]
    corpus = {
        e.chunk_id: {"text": e.text}
        for e in evidencias
    }
    ajustado = cobrir_definicao(
        pergunta, ranking, corpus, ["normativa"], 3
    )
    ids = [item["chunk_id"] for item in ajustado[:3]]
    assert "definicao" in ids
    assert {i["chunk_id"]: i["rrf_score"] for i in ajustado} == {
        i["chunk_id"]: i["rrf_score"] for i in ranking
    }

    recuperadas = [e for e in evidencias if e.chunk_id in ids]
    conteudo = cobrir_selecao_definicao(
        pergunta, json.dumps({"chunk_ids": ["regra"]}),
        recuperadas, ["normativa"],
    )
    resposta, fontes = preparar_selecao_extrativa(
        conteudo, recuperadas, pergunta=pergunta
    )
    assert "Parágrafo único. Exceções." in resposta
    assert "XLI - pregão: bens e serviços comuns;" in resposta
    assert "leilão" not in resposta
    assert "diálogo competitivo" not in resposta
    assert {e.chunk_id for e in fontes} == {"regra", "definicao"}
