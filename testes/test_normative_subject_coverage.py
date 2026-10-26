import json
from types import SimpleNamespace

import pytest

from src.normative_selection import cobrir_selecao_definicao
from src.grounded_quotes import preparar_selecao_extrativa

PERGUNTA = "O que a lei estabelece sobre o pregão?"


def fontes():
    return [
        SimpleNamespace(
            chunk_id="aplicacao",
            natureza="normativa",
            text=(
                "Art. 29. Adota-se o pregão quando o objeto possuir "
                "padrões de desempenho e qualidade definidos. "
                "Parágrafo único. O pregão não se aplica aos casos "
                "expressamente ressalvados."
            ),
        ),
        SimpleNamespace(
            chunk_id="vigencia",
            natureza="normativa",
            text="Art. 194. Esta Lei entra em vigor na data de sua publicação.",
        ),
        SimpleNamespace(
            chunk_id="definicao",
            natureza="normativa",
            text="Art. 6º XLI - pregão: modalidade para bens e serviços comuns;",
        ),
    ]


@pytest.mark.parametrize("escolhidos", [
    ["vigencia"],
    ["definicao"],
    ["vigencia", "definicao"],
])
def test_cobre_assunto_sem_artigo_irrelevante(escolhidos):
    evidencias = fontes()
    conteudo = cobrir_selecao_definicao(
        PERGUNTA,
        json.dumps({"chunk_ids": escolhidos}),
        evidencias,
        ["normativa"],
    )
    assert set(json.loads(conteudo)["chunk_ids"]) == {
        "aplicacao", "definicao",
    }
    resposta, citadas = preparar_selecao_extrativa(
        conteudo, evidencias, pergunta=PERGUNTA,
    )
    assert evidencias[0].text in resposta
    assert "Parágrafo único" in resposta
    assert "Art. 194" not in resposta
    assert {e.chunk_id for e in citadas} == {
        "aplicacao", "definicao",
    }


def test_pedido_de_artigo_especifico_preservado():
    original = json.dumps({"chunk_ids": ["vigencia"]})
    assert cobrir_selecao_definicao(
        "O que o artigo 194 estabelece?",
        original, fontes(), ["normativa"],
    ) == original


def test_id_inventado_nao_e_corrigido_silenciosamente():
    with pytest.raises(ValueError):
        cobrir_selecao_definicao(
            PERGUNTA,
            json.dumps({"chunk_ids": ["inventado"]}),
            fontes(), ["normativa"],
        )
