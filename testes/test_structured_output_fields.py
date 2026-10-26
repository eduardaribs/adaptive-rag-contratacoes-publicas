from src.router import planejar_consulta

PERGUNTA = (
    "Liste as contratações de pregão eletrônico publicadas "
    "no RJ em março de 2026. "
    "Mostre apenas número de controle PNCP, órgão, objeto, "
    "modalidade e data de publicação."
)


def planejar(pergunta):
    return planejar_consulta(
        pergunta,
        analise={
            "query": pergunta,
            "query_id": "q_campos",
            "routes": ["estruturada"],
            "filters": {"uf": "RJ"},
            "is_refusal": False,
        },
    )


def test_campos_de_saida_nao_viram_contagem_ou_filtros():
    plano = planejar(PERGUNTA)

    assert plano["estrategia"] == "consulta_estruturada"
    assert plano["operacao"] == "listar"
    assert set(plano["campos"]) == {
        "id_pncp", "orgao", "objeto", "modalidade", "data_publicacao"
    }
    assert plano["filtros"] == {
        "uf": "RJ",
        "data_inicial": "2026-03-01",
        "data_final": "2026-03-31",
        "modalidade_id": 6,
    }


def test_contagem_e_listagem_reais_ainda_exigem_esclarecimento():
    plano = planejar(
        "Liste as contratações e informe o total de contratações. "
        "Mostre apenas número de controle PNCP e objeto."
    )
    assert plano["necessita_esclarecimento"] is True


def test_filtro_de_orgao_apos_campos_nao_e_removido():
    plano = planejar(PERGUNTA + " Apenas do órgão INCA.")

    assert plano["necessita_esclarecimento"] is True


def test_filtro_desconhecido_dentro_da_clausula_nao_e_removido():
    plano = planejar(
        "Liste as contratações. "
        "Mostre apenas objeto e órgão INCA."
    )
    assert plano["necessita_esclarecimento"] is True
