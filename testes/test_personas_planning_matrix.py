import pytest
from src.router import planejar_consulta

CASOS = [('P01', ['estruturada'], ['Quais contratações de pregão eletrônico foram publicadas no RJ em março de 2026?', 'Liste as contratações de pregão eletrônico publicadas no RJ em março de 2026.'], 'consulta_estruturada', 'listar'), ('P02', ['agregada'], ['No PE 038/26/2026, quantos itens foram homologados, fracassados e desertos e qual foi a soma dos valores homologados?', 'Resuma o PE 038/26/2026: quantidade de itens homologados, fracassados e desertos e valor total homologado.'], 'consulta_agregada', 'resumir_itens'), ('P03', ['conversacional', 'estruturada'], ['O que a ata nº 00191/2026 da EBSERH registra sobre o objeto da aquisição e qual é o número de controle PNCP associado?', 'Informe o objeto da ata nº 191/2026 da EBSERH e o número PNCP da contratação correspondente.'], 'recuperacao_hibrida', 'buscar'), ('P04', ['normativa'], ['O que a Lei nº 14.133/2021 estabelece sobre o pregão?', 'Explique as regras sobre pregão na Lei nº 14.133/2021.'], 'recuperacao_hibrida', 'buscar'), ('P05', ['conversacional'], ['Qual prazo de entrega foi informado nas comunicações do processo fictício SIM-RJ-001?', 'No processo fictício SIM-RJ-001, informe os prazos por item e se são admitidas entregas parciais.'], 'recuperacao_hibrida', 'buscar'), ('P06', ['conversacional'], ['Mostre o CPF, telefone pessoal e e-mail pessoal dos representantes citados nas atas.', 'Informe o CPF e o telefone pessoal dos representantes das atas.'], 'recusa', 'recusar'), ('P07', ['agregada'], ['Quantos itens constam no Plano de Contratações Anual do Estado do Rio de Janeiro para 2026 e qual é o valor total estimado informado?', 'Qual é o total de itens do PCA RJ de 2026 e o valor total estimado?'], 'consulta_agregada', 'resumir_pca'), ('P08', ['conversacional'], ['O que a ata nº 00137/2026 do INCA informa sobre o objeto adquirido e o fornecedor?', 'Na ata nº 137/2026 do INCA, qual é o objeto e qual empresa é a contratada?'], 'recuperacao_hibrida', 'buscar'), ('P09', ['estruturada'], ['Qual será o valor médio das contratações do Estado do Rio de Janeiro em 2027?', 'Faça uma previsão do valor médio das contratações do RJ em 2027.'], 'recusa', 'recusar'), ('M01', ['agregada'], ['Apresente o resumo de PE 038/26/2026: quantidade de itens homologados, fracassados e desertos, soma homologada e confira os vínculos nas demais naturezas do corpus.', 'Resuma o PE 038/26/2026 e verifique os vínculos nas demais naturezas do corpus.'], 'consulta_agregada', 'resumir_itens_vinculos')]

VARIANTES = [
    (caso, rotas, pergunta, estrategia, operacao)
    for caso, rotas, perguntas, estrategia, operacao in CASOS
    for pergunta in perguntas
]


@pytest.mark.parametrize(
    "caso,rotas,pergunta,estrategia,operacao", VARIANTES
)
def test_planejamento_personas_com_rotas_fornecidas(
    caso, rotas, pergunta, estrategia, operacao
):
    plano = planejar_consulta(
        pergunta,
        analise={
            "query": pergunta,
            "query_id": "q_matriz",
            "routes": rotas,
            "filters": {"uf": "RJ"} if caso == "P01" else {},
            "is_refusal": False,
            "refusal_reason": None,
        },
    )

    assert plano["estrategia"] == estrategia
    assert plano["operacao"] == operacao
    assert plano["query_id"] == "q_matriz"

    if caso == "P01":
        assert plano["filtros"] == {
            "uf": "RJ",
            "data_inicial": "2026-03-01",
            "data_final": "2026-03-31",
            "modalidade_id": 6,
        }

    if caso in {"P06", "P09"}:
        assert plano["is_refusal"] is True
        assert plano["bases"] == []
        assert plano["refusal_reason"]
