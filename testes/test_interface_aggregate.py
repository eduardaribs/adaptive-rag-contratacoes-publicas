from copy import deepcopy

import pytest

from app.interface_results import (
    preparar_agregado,
    status_consulta,
    tabela_consulta,
)
from app import pipeline_adapter


def resultado_itens():
    return {
        "query": "Resumo do PE 038/26/2026.",
        "query_id": "q_agregada_interface",
        "run_id": "run_agregada_interface",
        "executado": True,
        "estrategia": "consulta_agregada",
        "operacao": "resumir_itens",
        "routes": ["agregada"],
        "filtros_aplicados": {
            "id_contratacao_pncp": "42498600000171-1-000757/2026"
        },
        "total_base": 19,
        "itens_total": 19,
        "homologados": 8,
        "fracassados": 9,
        "desertos": 2,
        "valor_total_homologado": "141002.08",
        "homologados_sem_valor": 0,
        "soma_completa": True,
        "fontes": ["itens.csv"],
        "referencias": ["https://pncp.gov.br/editais/42498600000171/2026/757"],
        "plano": {"processo_informado": "PE 038/26/2026"},
    }


def test_apresentacao_preserva_calculo_contexto_e_original():
    original = resultado_itens()
    copia = deepcopy(original)

    resultado = preparar_agregado(original)

    assert original == copia
    assert resultado["valor_total_homologado"] == "141002.08"
    assert resultado["itens_total"] == 19
    assert resultado["query_id"] == original["query_id"]
    assert resultado["run_id"] == original["run_id"]
    assert resultado["fontes_agregadas"] == ["itens.csv"]
    assert resultado["filters"] == original["filtros_aplicados"]
    assert "141.002,08" in resultado["answer"]
    assert "PE 038/26/2026" in resultado["answer"]
    assert "Consulta agregada" in status_consulta(resultado)
    assert tabela_consulta(resultado)["headers"] == [
        "indicador", "resultado"
    ]
    assert ["Homologados", 8] in tabela_consulta(resultado)["data"]


def test_pca_preserva_quatro_casas_decimais_e_recorte():
    original = {
        "operacao": "resumir_pca",
        "total_itens": 36994,
        "valor_total_estimado": "55968524178.3319",
        "itens_sem_valor": 0,
        "soma_completa": True,
        "fontes": ["pca.csv"],
        "plano": {
            "recorte_fonte": {"documento": "PCA", "uf": "RJ", "ano": 2026}
        },
    }

    resultado = preparar_agregado(original)

    assert resultado["valor_total_estimado"] == "55968524178.3319"
    assert "55.968.524.178,3319" in resultado["answer"]
    assert "Recorte associado à fonte" in resultado["answer"]


def test_soma_incompleta_e_explicita():
    original = resultado_itens()
    original["soma_completa"] = False
    original["homologados_sem_valor"] = 1

    resultado = preparar_agregado(original)

    assert "soma incompleta" in resultado["answer"]
    assert resultado["homologados_sem_valor"] == 1


def test_m01_preserva_vinculos_e_limitacao():
    original = resultado_itens()
    original["operacao"] = "resumir_itens_vinculos"
    original["total_chunks_verificados"] = 2125
    original["verificacao_vinculos"] = {
        "correspondencias": {
            "estruturada": [],
            "agregada": [{"chunk_id": "item_1"}],
            "conversacional": [],
            "normativa": [],
        },
        "observacao": (
            "Ausência de vínculo por identificador não comprova "
            "inexistência de documentos relacionados."
        ),
    }

    resultado = preparar_agregado(original)

    assert resultado["verificacao_vinculos"] == original["verificacao_vinculos"]
    assert "2125" in resultado["answer"]
    assert original["verificacao_vinculos"]["observacao"] in resultado["answer"]


@pytest.mark.parametrize("top_k", [1, 3, 5])
def test_adaptador_agregado_nao_chama_geracao(monkeypatch, top_k):
    original = resultado_itens()

    monkeypatch.setattr(
        pipeline_adapter,
        "executar_consulta",
        lambda **kwargs: deepcopy(original),
    )

    def nao_gerar(**kwargs):
        raise AssertionError("Cálculo agregado não deve chamar geração.")

    monkeypatch.setattr(pipeline_adapter, "gerar_resposta", nao_gerar)

    resultado = pipeline_adapter.executar_pipeline(
        original["query"], top_k=top_k
    )

    assert resultado["estrategia"] == "consulta_agregada"
    assert resultado["itens_total"] == 19
    assert resultado["valor_total_homologado"] == "141002.08"
    assert resultado["query_id"] == original["query_id"]
    assert resultado["run_id"] == original["run_id"]
    assert resultado["evidences"] == []
