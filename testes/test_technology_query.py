from copy import deepcopy

from src.query_executor import executar_consulta
from src.structured_query import consultar_registros
from src.technology_classifier import VERSAO_CRITERIO


def criterio():
    return {
        "implementacao": VERSAO_CRITERIO,
        "regra_principal": (
            "Classificar TIC por evidência contextual "
            "nos campos prioritários."
        ),
    }


def base():
    return [
        {
            "id_pncp": "1",
            "ano_compra": "2026",
            "municipio": "Rio de Janeiro",
            "objeto": "Aquisição de servidor rack.",
            "fonte_original": "teste.json",
        },
        {
            "id_pncp": "2",
            "ano_compra": "2026",
            "municipio": "Rio de Janeiro",
            "objeto": "Contratação de serviços de informática.",
            "fonte_original": "teste.json",
        },
        {
            "id_pncp": "3",
            "ano_compra": "2026",
            "municipio": "Rio de Janeiro",
            "objeto": "Contratação de sistema de refrigeração.",
            "fonte_original": "teste.json",
        },
        {
            "id_pncp": "4",
            "ano_compra": "2025",
            "municipio": "Niterói",
            "objeto": "Aquisição de computadores.",
            "fonte_original": "teste.json",
        },
    ]


def executar(pergunta, registros, top_k=1):
    return executar_consulta(
        pergunta,
        base=registros,
        criterio_tecnologia=criterio(),
        analise={
            "query_id": "q_tic_integracao",
            "routes": ["estruturada"],
            "filters": {},
            "is_refusal": False,
        },
        top_k=top_k,
    )


def test_contagem_respeita_ano_e_independe_top_k():
    registros = base()
    original = deepcopy(registros)

    for limite in (1, 3, 5):
        resultado = executar(
            "Quantas contratações de tecnologia têm ano da compra 2026?",
            registros,
            top_k=limite,
        )

        assert resultado["executado"] is True
        assert resultado["total"] == 2
        assert resultado["total_base"] == 4
        assert resultado["resumo_tecnologia"]["registros_no_recorte"] == 3
        assert resultado["resumo_tecnologia"]["revisao"] == 1
        assert resultado["filtros_aplicados"]["ano_compra"] == 2026
        assert resultado["criterio_objeto"]
        assert registros == original


def test_listagem_preserva_campos_paginacao_e_evidencias():
    primeira = executar(
        "Liste as contratações de tecnologia de 2026; "
        "página 1; 1 registro por página; mostre apenas objeto.",
        base(),
    )
    segunda = executar(
        "Liste as contratações de tecnologia de 2026; "
        "página 2; 1 registro por página; mostre apenas objeto.",
        base(),
    )

    assert primeira["executado"] and segunda["executado"]
    assert primeira["total"] == segunda["total"] == 2
    assert primeira["total_paginas"] == segunda["total_paginas"] == 2
    assert primeira["campos"] == segunda["campos"] == ["objeto"]
    assert primeira["registros"] == [{"objeto": "Aquisição de servidor rack."}]
    assert segunda["registros"] == [{
        "objeto": "Contratação de serviços de informática."
    }]
    assert primeira["referencias"][0]["id_pncp"] == "1"
    assert segunda["referencias"][0]["id_pncp"] == "2"

    for resultado in (primeira, segunda):
        classificacao = resultado["classificacoes_tecnologia"][0]
        assert classificacao["id_pncp"] == resultado["referencias"][0]["id_pncp"]
        assert classificacao["campo_evidencia"] == "objeto"
        assert classificacao["fonte"] == "teste.json"


def test_servicos_nao_incluem_aquisicao_de_bens():
    resultado = executar(
        "Quantas contratações envolvem serviços de tecnologia?",
        base(),
    )

    assert resultado["executado"] is True
    assert resultado["total"] == 1
    assert resultado["criterio_tecnologia"]["tipo"] == "servico_proposto"
    assert resultado["classificacoes_tecnologia"][0]["id_pncp"] == "2"


def test_sem_correspondencia_nao_inventa_resultado():
    resultado = executar(
        "Liste as contratações de tecnologia com ano da compra 2024.",
        base(),
    )

    assert resultado["executado"] is True
    assert resultado["total"] == 0
    assert resultado["registros"] == []
    assert resultado["classificacoes_tecnologia"] == []


def test_resumo_contextual_respeita_filtro_municipal():
    resultado = consultar_registros(
        base(),
        filtros={"municipio": "Niterói"},
        criterio_tecnologia={
            "implementacao": VERSAO_CRITERIO,
            "descricao": "Critério contextual operacional.",
            "tipo": "todos",
        },
    )

    assert resultado["total"] == 1
    assert resultado["resumo_tecnologia"]["registros_no_recorte"] == 1
    assert resultado["classificacoes_tecnologia"][0]["id_pncp"] == "4"
