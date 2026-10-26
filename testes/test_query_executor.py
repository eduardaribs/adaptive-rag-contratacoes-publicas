import pytest

from src.query_executor import executar_plano


@pytest.fixture
def base():
    return [
        {
            "id_pncp": str(numero),
            "objeto": "Serviço de teste",
            "ano_compra": "2026",
            "fonte_original": "teste.json",
        }
        for numero in range(1, 6)
    ]


def test_contagem_independente_de_top_k(base):
    plano = {
        "bases": ["estruturada"],
        "estrategia": "consulta_estruturada",
        "operacao": "contar",
        "filtros": {},
    }

    resultados = [
        executar_plano(
            "Quantas contratações existem?",
            plano,
            base=base,
            top_k=limite,
        )
        for limite in (1, 3, 5)
    ]

    assert [r["total"] for r in resultados] == [5, 5, 5]
    assert all(r["registros"] == [] for r in resultados)


def test_listagem_usa_paginacao_e_campos_do_plano(base):
    resultado = executar_plano(
        "Liste os objetos das contratações de 2026.",
        {
            "bases": ["estruturada"],
            "estrategia": "consulta_estruturada",
            "operacao": "listar",
            "filtros": {"ano_compra": 2026},
            "campos": ["objeto"],
            "pagina": 1,
            "tamanho_pagina": 4,
        },
        base=base,
        top_k=1,
    )

    assert resultado["total"] == 5
    assert len(resultado["registros"]) == 4
    assert all(
        set(registro) == {"objeto"}
        for registro in resultado["registros"]
    )


def test_pergunta_aberta_segue_para_recuperacao():
    chamadas = []

    def recuperador(**kwargs):
        chamadas.append(kwargs)
        return {
            "routes": ["estruturada"],
            "evidences": [{"chunk_id": "vidraca_1"}],
        }

    pergunta = "Tem contratação relacionada a reparo de vidraça?"

    resultado = executar_plano(
        pergunta,
        {
            "estrategia": "recuperacao_hibrida",
            "operacao": "buscar",
        },
        top_k=3,
        fetch_k=50,
        recuperador=recuperador,
    )

    assert len(chamadas) == 1
    assert chamadas[0]["pergunta"] == pergunta
    assert chamadas[0]["top_k"] == 3
    assert resultado["evidences"][0]["chunk_id"] == "vidraca_1"
    assert resultado["estrategia"] == "recuperacao_hibrida"


def test_combinada_executa_estruturada_e_hibrida(base):
    chamadas = []

    def recuperador(**kwargs):
        chamadas.append(kwargs)
        return {
            "query_id": "q_combinada",
            "routes": ["normativa"],
            "evidences": [{"chunk_id": "norma_1"}],
        }

    plano = {
        "bases": ["normativa", "estruturada"],
        "estrategia": "combinada",
        "operacao": "contar",
        "filtros": {"ano_compra": 2026},
        "rotas_recuperacao": ["normativa"],
        "query_id": "q_combinada",
    }

    resultado = executar_plano(
        "Quantas contratações existem e o que a norma diz sobre elas?",
        plano,
        base=base,
        top_k=2,
        fetch_k=10,
        recuperador=recuperador,
        analise_pronta={
            "query_id": "q_combinada",
            "routes": ["normativa", "estruturada"],
            "filters": {},
            "is_refusal": False,
        },
        run_id="run_combinada",
    )

    assert len(chamadas) == 1
    assert chamadas[0]["top_k"] == 2
    assert chamadas[0]["fetch_k"] == 10
    assert chamadas[0]["run_id"] == "run_combinada"
    assert chamadas[0]["analise_pronta"]["routes"] == ["normativa"]

    assert resultado["estrategia"] == "combinada"
    assert resultado["operacao"] == "contar"
    assert resultado["total"] == 5
    assert resultado["registros"] == []
    assert resultado["evidences"] == [{"chunk_id": "norma_1"}]
    assert resultado["evidencias"] == [{"chunk_id": "norma_1"}]
    assert resultado["estruturada"]["total"] == 5
    assert resultado["hibrida"]["estrategia"] == "recuperacao_hibrida"
    assert resultado["query_id"] == "q_combinada"
    assert resultado["run_id"] == "run_combinada"

def test_combinada_separa_filtros_estruturados_da_recuperacao(base):
    chamadas = []

    def recuperador(**kwargs):
        chamadas.append(kwargs)
        return {
            "query_id": "q_filtros_separados",
            "routes": ["normativa"],
            "evidences": [{"chunk_id": "norma_mei_1"}],
        }

    plano = {
        "bases": ["normativa", "estruturada"],
        "estrategia": "combinada",
        "operacao": "contar",
        "filtros": {"ano_compra": 2026},
        "rotas_recuperacao": ["normativa"],
        "query_id": "q_filtros_separados",
    }

    analise_pronta = {
        "query_id": "q_filtros_separados",
        "routes": ["normativa", "estruturada"],
        "filters": {},
        "is_refusal": False,
    }

    resultado = executar_plano(
        "Quantas contratações existem em 2026 "
        "e o que a legislação diz sobre MEI?",
        plano,
        base=base,
        recuperador=recuperador,
        analise_pronta=analise_pronta,
        run_id="run_filtros_separados",
    )

    assert resultado["estruturada"]["total"] == 5
    assert resultado["estruturada"]["filtros_aplicados"] == {
        "ano_compra": 2026
    }

    assert len(chamadas) == 1

    analise_recuperacao = chamadas[0]["analise_pronta"]

    assert analise_recuperacao["routes"] == ["normativa"]
    assert analise_recuperacao["filters"] == {}
    assert "ano_compra" not in analise_recuperacao["filters"]

    assert resultado["evidences"] == [
        {"chunk_id": "norma_mei_1"}
    ]
    assert resultado["query_id"] == "q_filtros_separados"
    assert resultado["run_id"] == "run_filtros_separados"


def test_combinada_listagem_preserva_paginacao_e_evidencias(base):
    def recuperador(**kwargs):
        return {
            "routes": ["conversacional"],
            "evidences": [{"chunk_id": "ata_1"}],
        }

    resultado = executar_plano(
        "Liste as contratações e mostre o que foi discutido nas atas.",
        {
            "bases": ["conversacional", "estruturada"],
            "estrategia": "combinada",
            "operacao": "listar",
            "filtros": {"ano_compra": 2026},
            "campos": ["objeto"],
            "pagina": 2,
            "tamanho_pagina": 2,
            "rotas_recuperacao": ["conversacional"],
        },
        base=base,
        recuperador=recuperador,
    )

    assert resultado["total"] == 5
    assert resultado["registros"] == [
        {"objeto": "Serviço de teste"},
        {"objeto": "Serviço de teste"},
    ]
    assert resultado["evidences"] == [{"chunk_id": "ata_1"}]
    assert resultado["estruturada"]["pagina"] == 2
    assert resultado["estruturada"]["total_paginas"] == 3


def test_combinada_exige_base_estruturada(base):
    with pytest.raises(ValueError, match="exige a base estruturada"):
        executar_plano(
            "Quantas existem e o que diz a norma?",
            {
                "bases": ["normativa"],
                "estrategia": "combinada",
                "operacao": "contar",
                "rotas_recuperacao": ["normativa"],
            },
            base=base,
            recuperador=lambda **kwargs: {},
        )


def test_combinada_exige_rota_de_recuperacao(base):
    with pytest.raises(ValueError, match="rota de recuperação"):
        executar_plano(
            "Quantas contratações existem?",
            {
                "bases": ["estruturada"],
                "estrategia": "combinada",
                "operacao": "contar",
            },
            base=base,
            recuperador=lambda **kwargs: {},
        )


def test_rejeita_estrategia_desconhecida():
    with pytest.raises(ValueError):
        executar_plano(
            "Uma pergunta.",
            {"estrategia": "inventada"},
        )


def test_rejeita_base_incompativel(base):
    with pytest.raises(ValueError):
        executar_plano(
            "Quantos registros?",
            {
                "bases": ["normativa"],
                "estrategia": "consulta_estruturada",
                "operacao": "contar",
            },
            base=base,
        )
