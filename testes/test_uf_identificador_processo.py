import pytest
from src.router import _extrair_uf_explicita, _validar_filtros_contra_pergunta


@pytest.mark.parametrize("pergunta,esperado", [
    ("No processo fictício SIM-RJ-001, informe os prazos.", None),
    ("Consulte o processo TESTE-RJ-987.", None),
    ("No processo fictício SIM-RJ-001, localizado no RJ, informe os prazos.", "RJ"),
    ("Quais contratações foram publicadas no RJ?", "RJ"),
    ("Liste contratações do Rio de Janeiro.", "RJ"),
    ("Consulte o processo TESTE-SP-987.", None),
])
def test_uf_distingue_localizacao_de_identificador(pergunta, esperado):
    assert _extrair_uf_explicita(pergunta) == esperado


def test_remove_uf_sugerida_sem_localizacao_explicita():
    filtros = _validar_filtros_contra_pergunta(
        "No processo fictício SIM-RJ-001, informe os prazos.",
        {"uf": "RJ"},
    )
    assert filtros["uf"] is None
