
import json
from types import SimpleNamespace

import pytest
from src.grounded_quotes import (
    _recortar_contratada_marca,
    preparar_selecao_extrativa,
)
from src.schema import SourceEvidence

PERGUNTA = (
    "Na ata nº 99/2026 do órgão, qual empresa é a contratada "
    "e qual é a marca ou fabricante do rodízio?"
)
CONSULTA = (
    "na ata n 99/2026 do orgao, qual empresa e a contratada "
    "e qual e a marca ou fabricante do rodizio?"
)
CONTRATADA = (
    "Condições gerais extensas. "
    "e de outro lado a EMPRESA EXEMPLO LTDA, inscrita no CNPJ, "
    "doravante denominada CONTRATADA. Outras cláusulas."
)
MARCA = (
    "Código Especificação Marca Modelo Unidade Quantidade. "
    "MARCA FABRICANTE DO RODIZIO RODAS XYZ - UN 10. "
    "Condições de prorrogação."
)


def montar(texto_contratada=CONTRATADA, texto_marca=MARCA):
    evidencias = [
        SourceEvidence(
            chunk_id="empresa", text=texto_contratada,
            natureza="conversacional", source_file="ata.pdf",
        ),
        SourceEvidence(
            chunk_id="produto", text=texto_marca,
            natureza="conversacional", source_file="ata.pdf",
        ),
    ]
    return evidencias


def test_recorte_integrado_preserva_papeis_citacoes_e_literalidade():
    evidencias = montar()
    texto, _ = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["empresa", "produto"]}),
        evidencias, pergunta=PERGUNTA,
    )
    assert "EMPRESA EXEMPLO LTDA" in texto
    assert "MARCA FABRICANTE DO RODIZIO RODAS XYZ" in texto
    assert "[Fonte: empresa]" in texto
    assert "[Fonte: produto]" in texto
    assert "Condições gerais extensas" not in texto
    assert "Condições de prorrogação" not in texto
    assert len(texto) < 600


@pytest.mark.parametrize("alteracao", [
    "sem_contratada", "sem_marca", "duas_marcas",
])
def test_campos_ausentes_ou_ambiguos_nao_sao_recortados(alteracao):
    contratada = CONTRATADA
    marca = MARCA
    if alteracao == "sem_contratada":
        contratada = "Documento sem identificação da contratada."
    elif alteracao == "sem_marca":
        marca = "Documento sem marca."
    else:
        marca += " MARCA FABRICANTE DO RODIZIO OUTRA MARCA - UN 2."
    evidencias = montar(contratada, marca)
    por_id = {e.chunk_id: e for e in evidencias}
    trechos = [{"chunk_id": e.chunk_id, "trecho": e.text} for e in evidencias]
    assert _recortar_contratada_marca(CONSULTA, trechos, por_id) is None


def test_pedido_adicional_nao_e_descartado_pelo_recorte():
    evidencias = montar()
    consulta = CONSULTA.rstrip("?") + " e qual e o valor unitario?"
    por_id = {e.chunk_id: e for e in evidencias}
    trechos = [{"chunk_id": e.chunk_id, "trecho": e.text} for e in evidencias]
    assert _recortar_contratada_marca(consulta, trechos, por_id) is None
