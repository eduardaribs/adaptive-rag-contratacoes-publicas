import json

from src.document_scope import escopar_ata


def natureza(chunk):
    return chunk["metadata"]["natureza"]


def documento(fonte, texto):
    return {
        "text": texto,
        "metadata": {
            "source_file": fonte,
            "natureza": "conversacional",
        },
    }


def test_ata_identificada_inclui_paginas_e_processo_exato():
    chunks = {
        "pagina_1": documento(
            "ata_a.pdf",
            "Ata de Registro de Preços - SEI nº 42/2026 "
            "Processo administrativo nº 12345.000678/2026-90",
        ),
        "pagina_2": documento("ata_a.pdf", "Descrição do objeto."),
        "outra_ata": documento("ata_b.pdf", "Ata nº 43/2026"),
        "vinculado": {
            "text": json.dumps({"processo": "12345000678202690"}),
            "metadata": {"natureza": "estruturada"},
        },
        "outro_registro": {
            "text": json.dumps({"processo": "99999000678202690"}),
            "metadata": {"natureza": "estruturada"},
        },
    }

    escopo = escopar_ata(
        "O que a ata nº 00042/2026 informa?", chunks, natureza
    )

    assert escopo["ids"] == {"pagina_1", "pagina_2", "vinculado"}


def test_ano_diferente_nao_identifica_documento():
    chunks = {
        "pagina": documento("ata.pdf", "Ata nº 42/2025"),
    }
    assert not escopar_ata(
        "O que a ata nº 42/2026 informa?", chunks, natureza
    )["ids"]


def test_pergunta_sem_ata_preserva_fluxo_existente():
    assert escopar_ata(
        "O que a lei estabelece sobre pregão?", {}, natureza
    ) is None


def test_identidade_ambigua_nao_escolhe_arbitrariamente():
    chunks = {
        "a": documento("a.pdf", "Ata nº 42/2026"),
        "b": documento("b.pdf", "Ata nº 42/2026"),
    }
    assert not escopar_ata(
        "O que a ata nº 42/2026 informa?", chunks, natureza
    )["ids"]
