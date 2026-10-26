from src.analytical_executor import executar_analitico


def test_distingue_registros_preenchidos_e_valores_distintos():
    resultado = executar_analitico({
        "fonte": "itens_pe",
        "tarefas": [
            {"id": "registros", "operacao": "contar"},
            {
                "id": "preenchidos", "operacao": "contar",
                "campo": "fornecedor",
            },
            {
                "id": "distintos", "operacao": "contar",
                "campo": "fornecedor", "distintos": True,
            },
        ],
    }, [
        {"fornecedor": "Empresa A"},
        {"fornecedor": "Empresa A"},
        {"fornecedor": "Empresa B"},
        {"fornecedor": None},
    ])
    valores = {r["id"]: r["valor"] for r in resultado["resultados"]}
    assert valores == {"registros": 4, "preenchidos": 3, "distintos": 2}
    assert resultado["resultados"][1]["valores_ausentes"] == 1


def test_contar_campo_numerico_nao_soma_seus_valores():
    resultado = executar_analitico({
        "fonte": "itens_pe",
        "tarefas": [{
            "id": "preenchidos", "operacao": "contar",
            "campo": "quantidade_homologada",
        }],
    }, [
        {"quantidade_homologada": "200"},
        {"quantidade_homologada": "100"},
        {"quantidade_homologada": None},
    ])
    assert resultado["resultados"][0]["valor"] == 2
