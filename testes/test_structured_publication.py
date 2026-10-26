import json
import pytest

from src.structured_query import consultar_registros


def registro(id_pncp, publicacao, atualizacao, ano, modalidade=6):
    return {
        "id_pncp": id_pncp,
        "ano_compra": str(ano),
        "data_publicacao": atualizacao,
        "fonte_original": "teste.json",
        "texto_integral": json.dumps({
            "dataPublicacaoPncp": publicacao,
            "dataAtualizacao": atualizacao,
            "modalidadeId": modalidade,
        }),
    }


def filtros():
    return {
        "data_inicial": "2026-03-01",
        "data_final": "2026-03-31",
        "modalidade_id": 6,
    }


def test_publicacao_nao_usa_atualizacao_nem_ano_compra():
    base = [
        registro("1", "2026-03-10T08:00:00",
                 "2026-04-15T09:00:00", 2025),
        registro("2", "2026-02-10T08:00:00",
                 "2026-03-15T09:00:00", 2026),
    ]

    resultado = consultar_registros(
        base,
        operacao="listar",
        filtros=filtros(),
        campos=["id_pncp", "data_publicacao"],
    )

    assert resultado["total"] == 1
    assert resultado["registros"] == [{
        "id_pncp": "1",
        "data_publicacao": "2026-03-10T08:00:00",
    }]
    assert base[0]["data_publicacao"] == "2026-04-15T09:00:00"


def test_intervalo_inclusivo_e_modalidade():
    base = [
        registro("1", "2026-03-01T00:00:00", "", 2026),
        registro("2", "2026-03-31T23:59:59", "", 2026),
        registro("3", "2026-04-01T00:00:00", "", 2026),
        registro("4", "2026-03-10T00:00:00", "", 2026, modalidade=8),
    ]

    assert consultar_registros(base, filtros=filtros())["total"] == 2


def test_publicacao_ausente_nao_e_substituida_por_atualizacao():
    base = [
        registro("1", None, "2026-03-15T00:00:00", 2026),
    ]

    resultado = consultar_registros(base, filtros=filtros())

    assert resultado["total"] == 0
    assert resultado["registros_sem_publicacao"] == 1


def test_intervalo_invertido_e_rejeitado():
    with pytest.raises(ValueError):
        consultar_registros([], filtros={
            "data_inicial": "2026-04-01",
            "data_final": "2026-03-01",
        })


def test_exige_registro_original_para_publicacao():
    with pytest.raises(ValueError, match="texto_integral"):
        consultar_registros(
            [{"id_pncp": "1", "data_publicacao": "2026-03-10"}],
            filtros=filtros(),
        )
