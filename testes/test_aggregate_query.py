import csv
from decimal import Decimal

import pytest

from src.aggregate_query import (
    decimal_csv,
    resumir_itens,
    resumir_pca,
)


def escrever_csv(caminho, campos, registros, separador):
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo, fieldnames=campos, delimiter=separador
        )
        escritor.writeheader()
        escritor.writerows(registros)
    return caminho


def criar_itens(tmp_path, registros):
    return escrever_csv(
        tmp_path / "itens.csv",
        [
            "id_contratacao_pncp", "numero_item", "situacao_item",
            "valor_total_homologado", "url_fonte",
        ],
        registros,
        ",",
    )


def item(numero, situacao, valor="", identificador="A"):
    return {
        "id_contratacao_pncp": identificador,
        "numero_item": str(numero),
        "situacao_item": situacao,
        "valor_total_homologado": valor,
        "url_fonte": "https://exemplo.test/fonte",
    }


def test_itens_filtra_contratacao_e_calcula_somente_homologados(tmp_path):
    caminho = criar_itens(tmp_path, [
        item(1, "Homologado", "100.10"),
        item(2, "Homologado", "20.05"),
        item(3, "Fracassado", "999"),
        item(4, "Deserto"),
        item(1, "Homologado", "500", identificador="B"),
    ])

    resultado = resumir_itens(caminho, id_contratacao="A")

    assert resultado["total_base"] == 5
    assert resultado["itens_total"] == 4
    assert resultado["homologados"] == 2
    assert resultado["fracassados"] == 1
    assert resultado["desertos"] == 1
    assert Decimal(resultado["valor_total_homologado"]) == Decimal("120.15")
    assert resultado["soma_completa"] is True
    assert resultado["referencias"] == ["https://exemplo.test/fonte"]


def test_itens_distingue_zero_de_valor_ausente(tmp_path):
    caminho = criar_itens(tmp_path, [
        item(1, "Homologado", "0"),
        item(2, "Homologado", ""),
    ])

    resultado = resumir_itens(caminho, id_contratacao="A")

    assert resultado["homologados"] == 2
    assert resultado["homologados_sem_valor"] == 1
    assert resultado["soma_completa"] is False
    assert Decimal(resultado["valor_total_homologado"]) == 0


def test_itens_sem_correspondencia(tmp_path):
    caminho = criar_itens(tmp_path, [item(1, "Homologado", "10")])

    resultado = resumir_itens(caminho, id_contratacao="inexistente")

    assert resultado["itens_total"] == 0
    assert resultado["homologados"] == 0
    assert resultado["referencias"] == []
    assert Decimal(resultado["valor_total_homologado"]) == 0


def test_itens_rejeita_duplicacao_na_mesma_contratacao(tmp_path):
    caminho = criar_itens(tmp_path, [
        item(1, "Homologado", "10"),
        item(1, "Deserto"),
    ])

    with pytest.raises(ValueError, match="duplicado"):
        resumir_itens(caminho, id_contratacao="A")


def test_itens_rejeita_situacao_desconhecida(tmp_path):
    caminho = criar_itens(tmp_path, [item(1, "Desconhecido")])

    with pytest.raises(ValueError, match="Situação"):
        resumir_itens(caminho, id_contratacao="A")


def test_pca_preserva_precisao_e_informa_ausencia(tmp_path):
    campo = "Valor Total Estimado (R$)"
    caminho = escrever_csv(
        tmp_path / "pca.csv",
        ["UASG", "Id do item no PCA", campo],
        [
            {"UASG": "1", "Id do item no PCA": "1", campo: "1.234,5678"},
            {"UASG": "1", "Id do item no PCA": "2", campo: "0,0001"},
            {"UASG": "2", "Id do item no PCA": "1", campo: "0"},
            {"UASG": "2", "Id do item no PCA": "2", campo: ""},
        ],
        ";",
    )

    resultado = resumir_pca(caminho)

    assert resultado["total_itens"] == 4
    assert Decimal(resultado["valor_total_estimado"]) == Decimal("1234.5679")
    assert resultado["itens_sem_valor"] == 1
    assert resultado["soma_completa"] is False


@pytest.mark.parametrize("valor", ["abc", "NaN", "Infinity"])
def test_rejeita_valores_invalidos(valor):
    with pytest.raises(ValueError):
        decimal_csv(valor, formato="decimal")


def test_rejeita_colunas_ausentes(tmp_path):
    caminho = escrever_csv(
        tmp_path / "invalido.csv",
        ["outra_coluna"],
        [{"outra_coluna": "1"}],
        ";",
    )

    with pytest.raises(ValueError, match="Colunas ausentes"):
        resumir_pca(caminho)


def test_rejeita_linha_csv_malformada(tmp_path):
    caminho = tmp_path / "malformado.csv"
    caminho.write_text(
        "UASG;Id do item no PCA;Valor Total Estimado (R$)\n"
        "1;2;10,00;campo_extra\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="malformada"):
        resumir_pca(caminho)
