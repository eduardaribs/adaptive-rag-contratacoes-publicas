import pytest

from src.document_context import preparar_contexto_pdf
from src.schema import SourceEvidence


def evidencia(identificador, texto, natureza="conversacional", fonte="ata.pdf"):
    return SourceEvidence(
        chunk_id=identificador,
        text=texto,
        natureza=natureza,
        source_file=fonte,
    )


def montar(evidencias):
    return "\n".join(e.text for e in evidencias)


def test_preserva_objeto_e_papel_explicito():
    entradas = [
        evidencia("empresa", (
            "Condições gerais sem relação direta.\n\n"
            "E de outro lado a EMPRESA A, doravante denominada CONTRATADA."
        )),
        evidencia("objeto", (
            "A presente ata tem por objeto o registro de preços "
            "para eventual aquisição de equipamentos."
        )),
        evidencia("ruido", "Condições administrativas. " * 100),
    ]
    selecionadas, detalhes = preparar_contexto_pdf(
        entradas,
        "Explique o que está previsto na ata e identifique a empresa contratada.",
        montar,
        limite=500,
    )
    ids = {e.chunk_id for e in selecionadas}
    assert {"empresa", "objeto"}.issubset(ids)
    assert len(montar(selecionadas)) <= 500
    assert any(not d["incluida_no_contexto"] for d in detalhes)


def test_nao_corta_paragrafo_grande():
    entrada = evidencia("grande", "Objeto e empresa contratada. " * 100)
    with pytest.raises(ValueError, match="cabe inteiro"):
        preparar_contexto_pdf(
            [entrada], "Qual é a empresa contratada?", montar, limite=500
        )


def test_nao_altera_original():
    texto = (
        "Informação administrativa.\n\n"
        "A ata tem por objeto o registro de preços."
        "\n\n" + "Texto secundário. " * 100
    )
    entrada = evidencia("original", texto)
    preparar_contexto_pdf(
        [entrada], "Qual é o objeto?", montar, limite=500
    )
    assert entrada.text == texto


def test_mensagens_txt_nao_sao_recortadas():
    entrada = evidencia("mensagem", "x" * 1000, fonte="mensagens.txt")
    selecionadas, detalhes = preparar_contexto_pdf(
        [entrada], "Qual é o prazo?", montar, limite=500
    )
    assert selecionadas == [entrada]
    assert detalhes == []


def test_resultado_calculado_nao_e_recortado():
    entrada = evidencia(
        "calculo", "x" * 1000, natureza="agregada", fonte="itens.csv"
    )
    selecionadas, detalhes = preparar_contexto_pdf(
        [entrada], "Qual é o total?", montar, limite=500
    )
    assert selecionadas == [entrada]
    assert detalhes == []
