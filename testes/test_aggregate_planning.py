import csv

import pytest

from src.router import planejar_consulta
from src.query_executor import executar_consulta, executar_plano


P02 = (
    "No PE 038/26/2026, quantos itens foram homologados, "
    "fracassados e desertos e qual foi a soma dos valores homologados?"
)
P07 = (
    "Quantos itens constam no Plano de Contratações Anual "
    "do Estado do Rio de Janeiro para 2026 "
    "e qual é o valor total estimado informado?"
)


def analise(pergunta):
    return {
        "query": pergunta,
        "query_id": "q_agregada",
        "routes": ["agregada"],
        "filters": {"ano": 2026, "uf": "RJ"},
        "is_refusal": False,
    }


def test_planeja_p02():
    plano = planejar_consulta(P02, analise=analise(P02))
    assert plano["estrategia"] == "consulta_agregada"
    assert plano["operacao"] == "resumir_itens"
    assert plano["filtros"] == {
        "id_contratacao_pncp": "42498600000171-1-000757/2026"
    }


def test_planeja_p07():
    plano = planejar_consulta(P07, analise=analise(P07))
    assert plano["estrategia"] == "consulta_agregada"
    assert plano["operacao"] == "resumir_pca"
    assert plano["filtros"] == {}
    assert plano["recorte_fonte"]["ano"] == 2026


@pytest.mark.parametrize("pergunta", [
    P07.replace("2026", "2027"),
    P07.replace("Rio de Janeiro", "São Paulo"),
    P07 + " Apenas do município de Niterói.",
    P02 + " Verifique também as atas relacionadas.",
])
def test_nao_ignora_pedidos_nao_suportados(pergunta):
    resultado = executar_consulta(
        pergunta,
        analise=analise(pergunta),
    )
    assert resultado["executado"] is False
    assert resultado["plano"]["necessita_esclarecimento"] is True


def test_pergunta_aberta_pca_preserva_recuperacao():
    pergunta = "Quais itens aparecem no Plano de Contratações Anual?"
    plano = planejar_consulta(pergunta, analise=analise(pergunta))
    assert plano["estrategia"] == "recuperacao_hibrida"


def test_executor_agregado_preserva_ids_e_independencia_top_k(
    tmp_path, monkeypatch
):
    import src.aggregate_query as aggregate

    caminho = tmp_path / "pca.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=[
                "UASG", "Id do item no PCA",
                "Valor Total Estimado (R$)",
            ],
            delimiter=";",
        )
        escritor.writeheader()
        escritor.writerows([
            {
                "UASG": "1", "Id do item no PCA": "1",
                "Valor Total Estimado (R$)": "0,0001",
            },
            {
                "UASG": "1", "Id do item no PCA": "2",
                "Valor Total Estimado (R$)": "10,0000",
            },
        ])

    original = aggregate.resumir_pca
    monkeypatch.setattr(
        aggregate,
        "resumir_pca",
        lambda arquivo: original(caminho),
    )

    def nao_recuperar(**kwargs):
        raise AssertionError("Consulta agregada não deve chamar o RAG.")

    for limite in (1, 3, 5):
        resultado = executar_consulta(
            P07,
            analise=analise(P07),
            top_k=limite,
            recuperador=nao_recuperar,
            run_id="run_agregada",
        )
        assert resultado["executado"] is True
        assert resultado["total_itens"] == 2
        assert resultado["valor_total_estimado"] == "10.0001"
        assert resultado["query_id"] == "q_agregada"
        assert resultado["run_id"] == "run_agregada"


def test_executor_rejeita_filtro_pca_nao_suportado():
    with pytest.raises(ValueError, match="não aceita filtros"):
        executar_plano(
            P07,
            {
                "bases": ["agregada"],
                "estrategia": "consulta_agregada",
                "operacao": "resumir_pca",
                "filtros": {"municipio": "Niterói"},
            },
        )
