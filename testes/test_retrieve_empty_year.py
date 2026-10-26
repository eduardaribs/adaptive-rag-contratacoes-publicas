import pytest

from src.retrieve import chunk_atende_filtros


def chunk(ano):
    return {
        "metadata": {
            "sensitivity": "publico",
            "natureza": "conversacional",
            "base_id": "base_conversacional",
            "source_file": "ata.pdf",
            "uf": "RJ",
            "ano": ano,
        }
    }


@pytest.mark.parametrize("ano", [None, "", "   "])
def test_ano_ausente_nao_elimina_documento(ano):
    assert chunk_atende_filtros(chunk(ano), {"ano": 2026})


@pytest.mark.parametrize("ano", [2026, "2026"])
def test_ano_conhecido_compativel_e_preservado(ano):
    assert chunk_atende_filtros(chunk(ano), {"ano": 2026})


@pytest.mark.parametrize("ano", [2025, "2025", "invalido"])
def test_ano_divergente_ou_invalido_e_rejeitado(ano):
    assert not chunk_atende_filtros(chunk(ano), {"ano": 2026})


def test_ano_vazio_nao_desativa_filtro_de_uf():
    assert not chunk_atende_filtros(
        chunk(""),
        {"ano": 2026, "uf": "SP"},
    )
