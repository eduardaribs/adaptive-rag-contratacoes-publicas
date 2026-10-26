import pytest

from src.router import planejar_consulta


def planejar(pergunta):
    return planejar_consulta(
        pergunta,
        analise={
            "query": pergunta,
            "query_id": "q_reformulacao",
            "routes": ["agregada"],
            "filters": {},
            "is_refusal": False,
        },
    )


@pytest.mark.parametrize("pergunta, operacao", [
    (
        "Qual é o total de itens do PCA RJ de 2026 "
        "e o valor total estimado?",
        "resumir_pca",
    ),
    (
        "Informe o total de itens no PCA do Estado do Rio de Janeiro "
        "para 2026 e informe o valor total estimado.",
        "resumir_pca",
    ),
    (
        "Resuma o PE 038/26/2026: quantidade de itens homologados, "
        "fracassados e desertos e valor total homologado.",
        "resumir_itens",
    ),
    (
        "Apresente o resumo de PE 038/26/2026: quantidade de itens "
        "homologados, fracassados e desertos, soma homologada "
        "e confira os vínculos nas demais naturezas do corpus.",
        "resumir_itens_vinculos",
    ),
])
def test_reformulacoes_preservam_operacao(pergunta, operacao):
    plano = planejar(pergunta)

    assert plano["estrategia"] == "consulta_agregada"
    assert plano["operacao"] == operacao
    assert plano["query_id"] == "q_reformulacao"


@pytest.mark.parametrize("pergunta", [
    "Qual é o total de itens do PCA RJ de 2027 "
    "e o valor total estimado?",
    "Qual é o total de itens do PCA RJ de 2026 "
    "e o valor total estimado? Apenas de Niterói.",
    "Resuma o PE 038/26/2026: quantidade de itens homologados, "
    "fracassados e desertos e valor total homologado. "
    "Apenas do fornecedor ANDES.",
    "Qual é o total de itens do PCA RJ de 2026 "
    "e o valor médio estimado?",
])
def test_nao_descarta_criterios_nao_suportados(pergunta):
    plano = planejar(pergunta)

    assert plano["estrategia"] != "consulta_agregada"
    assert (
        plano.get("necessita_esclarecimento")
        or plano.get("is_refusal")
    )
