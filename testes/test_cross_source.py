import pytest

from src.cross_source import verificar_vinculos

ID = "42498600000171-1-000757/2026"


def chunk(numero, natureza, texto):
    return {
        "chunk_id": str(numero),
        "text": texto,
        "metadata": {
            "natureza": natureza,
            "source_file": "teste.json",
        },
    }


def test_id_exato_identifica_vinculo():
    resultado = verificar_vinculos(
        [chunk(1, "conversacional", f"Ata referente a {ID}.")],
        id_contratacao=ID,
    )
    encontrados = resultado["correspondencias"]["conversacional"]
    assert len(encontrados) == 1
    assert encontrados[0]["vinculo"]["tipo"] == "id_pncp_exato"
    assert encontrados[0]["fonte"] == "teste.json"


def test_url_do_edital_identifica_vinculo():
    resultado = verificar_vinculos(
        [chunk(
            1, "conversacional",
            "Fonte: https://pncp.gov.br/editais/42498600000171/2026/757",
        )],
        id_contratacao=ID,
    )
    assert resultado["total_correspondencias"] == 1


def test_lei_generica_e_contratacao_diferente_nao_criam_vinculo():
    resultado = verificar_vinculos([
        chunk(1, "normativa", "Lei 14.133/2021: regras sobre pregão."),
        chunk(2, "estruturada", "42498600000171-1-000758/2026"),
        chunk(
            3, "conversacional",
            "https://outro.test/editais/42498600000171/2026/757",
        ),
    ], id_contratacao=ID)

    assert resultado["total_correspondencias"] == 0
    assert resultado["cobertura_por_natureza"]["normativa"] == 1


def test_percorre_todos_os_chunks_e_preserva_trecho():
    chunks = [
        chunk(i, "estruturada", "Sem vínculo.")
        for i in range(10)
    ]
    chunks.append(chunk(10, "agregada", ID))

    resultado = verificar_vinculos(chunks, id_contratacao=ID)

    assert resultado["total_chunks_verificados"] == 11
    assert resultado["correspondencias"]["agregada"][0]["trecho"] == ID


def test_rejeita_id_invalido():
    with pytest.raises(ValueError, match="PNCP"):
        verificar_vinculos([], id_contratacao="PE 038/26/2026")


def test_rejeita_chunks_duplicados():
    registro = chunk(1, "agregada", ID)
    with pytest.raises(ValueError, match="duplicados"):
        verificar_vinculos([registro, registro], id_contratacao=ID)
