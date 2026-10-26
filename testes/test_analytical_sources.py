import csv
from decimal import Decimal

import pytest

from src.analytical_sources import FONTES, carregar_fonte, executar_fonte


def criar_itens(tmp_path, linhas):
    caminho = tmp_path / FONTES["itens_pe"]["arquivo"]
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo, fieldnames=list(FONTES["itens_pe"]["colunas"])
        )
        escritor.writeheader()
        escritor.writerows(linhas)
    return caminho


def item(numero="1"):
    return {
        "id_contratacao_pncp": "contratacao_teste",
        "numero_item": numero,
        "situacao_item": "homologado",
        "quantidade_homologada": "2",
        "valor_unitario_homologado": "0.15",
        "valor_total_homologado": "0.30",
        "fornecedor": "Empresa de teste",
        "data_homologacao": "2026-03-10",
        "url_fonte": "https://exemplo.invalid",
    }


def test_leitura_preserva_decimal_data_e_hash(tmp_path):
    criar_itens(tmp_path, [item()])
    linhas, origem = carregar_fonte("itens_pe", raiz=tmp_path)
    assert linhas[0]["valor_total_homologado"] == Decimal("0.30")
    assert linhas[0]["data_homologacao"] == "2026-03-10"
    assert origem["linhas_lidas"] == 1
    assert len(origem["sha256"]) == 64


def test_rejeita_item_duplicado(tmp_path):
    criar_itens(tmp_path, [item(), item()])
    with pytest.raises(ValueError, match="duplicado"):
        carregar_fonte("itens_pe", raiz=tmp_path)


def test_rejeita_fonte_arbitraria():
    with pytest.raises(ValueError, match="não autorizada"):
        carregar_fonte("../../outro_arquivo")


def test_calculo_usa_todas_as_linhas_e_informa_origem(tmp_path):
    criar_itens(tmp_path, [item("1"), item("2")])
    resultado = executar_fonte({
        "fonte": "itens_pe",
        "tarefas": [{
            "id": "soma", "operacao": "somar",
            "campo": "valor_total_homologado",
        }],
    }, raiz=tmp_path)
    assert Decimal(resultado["resultados"][0]["valor"]) == Decimal("0.60")
    assert resultado["proveniencia"]["linhas_lidas"] == 2
