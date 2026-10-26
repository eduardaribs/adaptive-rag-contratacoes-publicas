from src.document_scope import escopar_documento


def natureza(chunk):
    return chunk["metadata"]["natureza"]


def chunk(texto, fonte, tipo="conversacional"):
    return {
        "text": texto,
        "metadata": {"source_file": fonte, "natureza": tipo},
    }


def test_processo_exato_preserva_partes_da_mesma_fonte():
    chunks = {
        "a": chunk("Processo fictício: ABC-RJ-001", "mensagem.txt"),
        "b": chunk("Continuação com entregas parciais.", "mensagem.txt"),
        "c": chunk("Processo ABC-RJ-0010", "outro.txt"),
        "d": chunk("ABC-RJ-001", "base.json", "estruturada"),
    }
    resultado = escopar_documento(
        "Informe os prazos do processo fictício ABC-RJ-001.",
        chunks, natureza,
    )
    assert resultado["ids"] == {"a", "b"}
    assert resultado["fontes"] == ["mensagem.txt"]


def test_processo_inexistente_nao_amplia_busca():
    resultado = escopar_documento(
        "Prazo do processo ABC-RJ-999?",
        {"a": chunk("ABC-RJ-001", "mensagem.txt")},
        natureza,
    )
    assert resultado["ids"] == set()


def test_fontes_ambiguas_nao_sao_selecionadas():
    resultado = escopar_documento(
        "Prazo do processo ABC-RJ-001?",
        {
            "a": chunk("ABC-RJ-001", "a.txt"),
            "b": chunk("ABC-RJ-001", "b.txt"),
        },
        natureza,
    )
    assert resultado["ids"] == set()


def test_pergunta_sem_identificador_preserva_busca_aberta():
    assert escopar_documento(
        "Quais os prazos de entrega?", {}, natureza,
    ) is None


def test_multiplos_processos_nao_escolhem_apenas_um():
    resultado = escopar_documento(
        "Compare o processo ABC-RJ-001 e o processo ABC-RJ-002.",
        {}, natureza,
    )
    assert resultado["ids"] == set()


def test_escopo_de_ata_permanece_funcionando():
    resultado = escopar_documento(
        "Objeto da ata nº 137/2026?",
        {"a": chunk("ATA Nº 137/2026", "ata.pdf")},
        natureza,
    )
    assert resultado["ids"] == {"a"}
