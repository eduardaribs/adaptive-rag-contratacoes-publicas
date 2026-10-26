from src.context_focus import focar_evidencias
from src.schema import SourceEvidence


def documento(natureza="normativa"):
    secoes = [
        "I - " + "Informação administrativa. " * 300,
        "II - Pregão: definição pertinente ao pedido.",
        "III - Outro conceito.",
        "IV - Serviço referido: a) condição aplicável; b) exceção preservada.",
        "V - Conceito adicional.",
        "VI - Último conceito.",
    ]
    return SourceEvidence(
        chunk_id="lei_chunk_1",
        source_file="lei.html",
        natureza=natureza,
        text="Art. 6º Definições.\n\n" + "\n\n".join(secoes),
        metadata={"origem": "teste"},
    )


def test_preserva_inciso_referenciado_com_condicoes_e_ids():
    original = documento()
    referencia = SourceEvidence(
        chunk_id="lei_chunk_2",
        natureza="normativa",
        text="A regra remete ao inciso IV.",
    )
    focadas, detalhes = focar_evidencias(
        [original, referencia], "Explique o pregão."
    )
    assert "Pregão: definição pertinente" in focadas[0].text
    assert (
        "IV - Serviço referido: a) condição aplicável; "
        "b) exceção preservada."
    ) in focadas[0].text
    assert focadas[0].chunk_id == original.chunk_id
    assert focadas[0].metadata == original.metadata
    assert focadas[0].source_file == original.source_file
    assert detalhes[0]["caracteres_enviados"] < len(original.text)


def test_nao_modifica_evidencia_original():
    original = documento()
    antes = original.model_dump()
    focar_evidencias([original], "Explique o pregão.")
    assert original.model_dump() == antes


def test_preserva_documento_sem_correspondencia():
    original = documento()
    focadas, _ = focar_evidencias(
        [original], "Explique astronomia."
    )
    assert focadas[0].text == original.text


def test_preserva_documento_nao_normativo():
    original = documento("conversacional")
    focadas, _ = focar_evidencias([original], "Explique o pregão.")
    assert focadas[0].text == original.text


def test_preserva_regra_curta_incluindo_excecao():
    original = SourceEvidence(
        chunk_id="regra",
        natureza="normativa",
        text="Aplica-se à situação descrita, exceto quando houver impedimento.",
    )
    focadas, _ = focar_evidencias([original], "Quando se aplica?")
    assert focadas[0].text == original.text


def test_lista_vazia():
    assert focar_evidencias([], "Explique.") == ([], [])
