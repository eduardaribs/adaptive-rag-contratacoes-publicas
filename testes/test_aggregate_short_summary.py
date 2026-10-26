import pytest

from src.router import planejar_consulta


def planejar(pergunta):
    return planejar_consulta(
        pergunta,
        analise={
            "query": pergunta,
            "query_id": "q_m01_curta",
            "routes": ["agregada"],
            "filters": {},
            "is_refusal": False,
        },
    )


@pytest.mark.parametrize("pergunta", [
    "Resuma o PE 038/26/2026 e verifique os vínculos "
    "nas demais naturezas do corpus.",
    "Resuma o PE 038/26/2026 e confira os vínculos "
    "com as demais naturezas de evidência do corpus.",
])
def test_resumo_curto_com_vinculos(pergunta):
    plano = planejar(pergunta)

    assert plano["estrategia"] == "consulta_agregada"
    assert plano["operacao"] == "resumir_itens_vinculos"
    assert plano["bases"] == ["agregada"]
    assert plano["filtros"] == {
        "id_contratacao_pncp": "42498600000171-1-000757/2026"
    }
    assert plano["query_id"] == "q_m01_curta"
    assert plano["metodo_vinculo"] == (
        "ID PNCP completo ou URL específica do edital"
    )


@pytest.mark.parametrize("complemento", [
    " Apenas do fornecedor ANDES.",
    " Apenas de Niterói.",
    " Calcule também o valor médio.",
])
def test_resumo_curto_nao_descarta_criterios(complemento):
    pergunta = (
        "Resuma o PE 038/26/2026 e verifique os vínculos "
        "nas demais naturezas do corpus."
        + complemento
    )
    plano = planejar(pergunta)

    assert plano["estrategia"] == "esclarecimento"
    assert plano["necessita_esclarecimento"] is True


def test_pedido_aberto_de_itens_preserva_busca():
    plano = planejar("Quais itens aparecem no PE 038/26/2026?")

    assert plano["estrategia"] == "recuperacao_hibrida"
    assert plano["operacao"] == "buscar"
