import json
from types import SimpleNamespace

import pytest
from src.grounded_quotes import preparar_selecao_extrativa


PERGUNTA = (
    "O que a ata nº 00137/2026 do INCA informa "
    "sobre o objeto adquirido e o fornecedor?"
)


def evidencias():
    return [
        SimpleNamespace(
            chunk_id="objeto_1",
            source_file="ata.pdf",
            natureza="conversacional",
            text=(
                "Cabeçalho. A presente Ata tem por objeto o registro "
                "de preços para eventual aquisição de mesas, "
                "especificadas no termo. Condições gerais."
            ),
        ),
        SimpleNamespace(
            chunk_id="fornecedor_1",
            source_file="ata.pdf",
            natureza="conversacional",
            text=(
                "Introdução. e de outro lado a EMPRESA EXEMPLO LTDA, "
                "inscrita no cadastro, doravante denominada CONTRATADA, "
                "resolvem celebrar o instrumento. Condições gerais."
            ),
        ),
        SimpleNamespace(
            chunk_id="fabricante_1",
            source_file="ata.pdf",
            natureza="conversacional",
            text="Marca e fabricante: FABRICANTE EXEMPLO.",
        ),
    ]


def apresentar(itens, pergunta=PERGUNTA):
    return preparar_selecao_extrativa(
        json.dumps({"chunk_ids": [item.chunk_id for item in itens]}),
        itens,
        pergunta=pergunta,
    )


def test_recorta_objeto_e_contratada_sem_confundir_fabricante():
    resposta, fontes = apresentar(evidencias())
    assert "aquisição de mesas" in resposta
    assert "EMPRESA EXEMPLO LTDA" in resposta
    assert "denominada CONTRATADA" in resposta
    assert "Condições gerais" not in resposta
    assert "FABRICANTE EXEMPLO" not in resposta
    assert [item.chunk_id for item in fontes] == [
        "objeto_1", "fornecedor_1",
    ]


def test_sem_contratada_preserva_trechos_disponiveis():
    itens = [evidencias()[0], evidencias()[2]]
    resposta, fontes = apresentar(itens)
    assert "Condições gerais" in resposta
    assert "FABRICANTE EXEMPLO" in resposta
    assert len(fontes) == 2


def test_pedido_adicional_nao_perde_informacoes_por_recorte():
    resposta, _ = apresentar(
        evidencias(),
        pergunta=(
            "O que a ata nº 00137/2026 informa sobre o objeto "
            "e o fornecedor, incluindo condições gerais?"
        ),
    )
    assert "Condições gerais" in resposta


def test_id_nao_recuperado_continua_rejeitado():
    with pytest.raises(ValueError, match="não foi recuperado"):
        preparar_selecao_extrativa(
            json.dumps({"chunk_ids": ["inventado"]}),
            evidencias(),
            pergunta=PERGUNTA,
        )


def test_reformulacao_recorta_campos_sem_json_ou_fabricante():
    itens = evidencias() + [
        SimpleNamespace(
            chunk_id="registro_estruturado",
            natureza="estruturada",
            source_file="registro.json",
            text=json.dumps({
                "objetoCompra": "Mesas",
                "outroCampo": "informação não solicitada",
            }),
        ),
    ]
    originais = [item.text for item in itens]
    resposta, fontes = apresentar(
        itens,
        pergunta=(
            "Na ata nº 137/2026 do INCA, qual é o objeto "
            "e qual empresa é a contratada?"
        ),
    )
    assert "aquisição de mesas" in resposta
    assert "EMPRESA EXEMPLO LTDA" in resposta
    assert "denominada CONTRATADA" in resposta
    assert "Condições gerais" not in resposta
    assert "outroCampo" not in resposta
    assert "FABRICANTE EXEMPLO" not in resposta
    assert [item.chunk_id for item in fontes] == [
        "objeto_1", "fornecedor_1",
    ]
    assert [item.text for item in itens] == originais


def test_reformulacao_com_pedido_adicional_preserva_textos():
    resposta, _ = apresentar(
        evidencias(),
        pergunta=(
            "Na ata nº 137/2026 do INCA, qual é o objeto "
            "e qual empresa é a contratada, incluindo condições gerais?"
        ),
    )
    assert "Condições gerais" in resposta
