import pytest

from src.structured_query import consultar_registros


@pytest.fixture
def base():
    return [
        {
            "id_pncp": "003",
            "orgao": "Órgão C",
            "municipio": "Niterói",
            "uf": "RJ",
            "ano_compra": "2026",
            "objeto": "Reparo de vidraças",
            "valor_estimado": None,
            "valor_homologado": None,
            "fonte_original": "corpus_teste.json",
        },
        {
            "id_pncp": "001",
            "orgao": "Órgão A",
            "municipio": "Nilópolis",
            "uf": "RJ",
            "ano_compra": "2026",
            "objeto": "Licenças de software",
            "valor_estimado": 500000,
            "valor_homologado": None,
            "fonte_original": "corpus_teste.json",
        },
        {
            "id_pncp": "002",
            "orgao": "Órgão B",
            "municipio": "Nilópolis",
            "uf": "RJ",
            "ano_compra": "2025",
            "objeto": "Serviços de informática",
            "valor_estimado": 700000,
            "valor_homologado": 0,
            "fonte_original": "corpus_teste.json",
        },
    ]


def test_contagem_usa_todos_os_registros(base):
    resultado = consultar_registros(base)
    assert resultado["total"] == 3
    assert resultado["registros"] == []


def test_filtros_combinados_e_acentos(base):
    resultado = consultar_registros(
        base,
        filtros={"municipio": "NILOPOLIS", "ano_compra": 2026},
    )
    assert resultado["total"] == 1


def test_selecao_de_campos_e_referencia(base):
    resultado = consultar_registros(
        base, operacao="listar", campos=["objeto"],
        filtros={"ano_compra": 2026},
    )
    assert resultado["total"] == 2
    assert all(set(r) == {"objeto"} for r in resultado["registros"])
    assert resultado["referencias"][0]["id_pncp"] == "001"


def test_paginacao_estavel_sem_omissao(base):
    paginas = [
        consultar_registros(
            base, operacao="listar", campos=["id_pncp"],
            pagina=p, tamanho_pagina=1,
        )
        for p in (1, 2, 3)
    ]
    ids = [r["registros"][0]["id_pncp"] for r in paginas]
    assert ids == ["001", "002", "003"]
    assert all(r["total"] == 3 for r in paginas)
    assert all(r["total_paginas"] == 3 for r in paginas)


def test_limite_estrito(base):
    resultado = consultar_registros(
        base,
        filtros={"valor_minimo": 500000},
        campo_valor="valor_estimado",
        minimo_inclusivo=False,
    )
    assert resultado["total"] == 1


def test_zero_nao_e_ausencia(base):
    resultado = consultar_registros(
        base,
        filtros={"valor_maximo": 0},
        campo_valor="valor_homologado",
    )
    assert resultado["total"] == 1


def test_exige_tipo_de_valor(base):
    with pytest.raises(ValueError):
        consultar_registros(base, filtros={"valor_minimo": 500000})


def test_sem_resultados(base):
    resultado = consultar_registros(
        base, operacao="listar", filtros={"ano_compra": 2035}
    )
    assert resultado["total"] == 0
    assert resultado["registros"] == []


def test_objeto_com_criterio_documentado(base):
    resultado = consultar_registros(
        base,
        filtros={"objeto_termos": ["software", "informática"]},
        criterio_objeto="Teste: objeto contém software OU informática.",
    )
    assert resultado["total"] == 2


def test_nao_ignora_filtro_desconhecido(base):
    with pytest.raises(ValueError):
        consultar_registros(base, filtros={"ano_publicacao": 2026})


def test_rejeita_ids_duplicados(base):
    with pytest.raises(ValueError):
        consultar_registros(base + [dict(base[0])])
