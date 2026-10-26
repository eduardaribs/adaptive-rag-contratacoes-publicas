import json
from types import SimpleNamespace

import pytest

from src.grounded_quotes import preparar_resposta_extrativa


@pytest.fixture
def evidencias():
    return [
        SimpleNamespace(
            chunk_id="lei_28",
            text="Art. 28. São modalidades de licitação: I - pregão;",
        ),
        SimpleNamespace(
            chunk_id="lei_29",
            text=(
                "Art. 29. Adota-se o pregão quando o objeto possuir "
                "padrões de desempenho e qualidade objetivamente definidos."
            ),
        ),
    ]


def resposta(chunk_id, trecho):
    return json.dumps({
        "trechos": [{"chunk_id": chunk_id, "trecho": trecho}]
    })


def test_trecho_literal_preserva_fonte(evidencias):
    texto, fontes = preparar_resposta_extrativa(
        resposta("lei_28", "São modalidades de licitação: I - pregão;"),
        evidencias,
    )
    assert "[Fonte: lei_28]" in texto
    assert [fonte.chunk_id for fonte in fontes] == ["lei_28"]


def test_aplicacao_nao_pode_ser_atribuida_ao_artigo_28(evidencias):
    with pytest.raises(ValueError, match="não está presente"):
        preparar_resposta_extrativa(
            resposta(
                "lei_28",
                "Adota-se o pregão quando o objeto possuir padrões "
                "de desempenho e qualidade objetivamente definidos.",
            ),
            evidencias,
        )


def test_trecho_inventado_e_rejeitado(evidencias):
    with pytest.raises(ValueError, match="não está presente"):
        preparar_resposta_extrativa(
            resposta("lei_29", "O pregão é obrigatório para todas as obras."),
            evidencias,
        )


def test_chunk_desconhecido_e_rejeitado(evidencias):
    with pytest.raises(ValueError, match="não foi recuperado"):
        preparar_resposta_extrativa(
            resposta("lei_999", "Art. 28."),
            evidencias,
        )


def test_espacos_de_formatacao_nao_invalidam_trecho(evidencias):
    texto, _ = preparar_resposta_extrativa(
        resposta("lei_28", "São modalidades\n de licitação: I - pregão;"),
        evidencias,
    )
    assert "São modalidades de licitação" in texto


@pytest.mark.parametrize("conteudo", [
    "Resposta livre sem JSON.",
    '{"trechos": []}',
    '{"trechos": [], "comentario": "Afirmação livre."}',
])
def test_formato_invalido_e_rejeitado(evidencias, conteudo):
    with pytest.raises(ValueError):
        preparar_resposta_extrativa(conteudo, evidencias)


def test_selecao_apresenta_texto_original(evidencias):
    from src.grounded_quotes import preparar_selecao_extrativa

    texto, fontes = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["lei_29"]}),
        evidencias,
    )

    assert evidencias[1].text in texto
    assert "[Fonte: lei_29]" in texto
    assert [fonte.chunk_id for fonte in fontes] == ["lei_29"]


@pytest.mark.parametrize("dados", [
    {"chunk_ids": ["lei_999"]},
    {"chunk_ids": []},
    {"chunk_ids": ["lei_29"], "comentario": "Texto inventado"},
    {"chunk_ids": [None]},
])
def test_selecao_invalida_e_rejeitada(evidencias, dados):
    from src.grounded_quotes import preparar_selecao_extrativa

    with pytest.raises(ValueError):
        preparar_selecao_extrativa(
            json.dumps(dados),
            evidencias,
        )
