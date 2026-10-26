from copy import deepcopy

import pytest

from src.technology_classifier import classificar_registro


@pytest.mark.parametrize("objeto", [
    "Aquisição de servidor rack de alto desempenho.",
    "Contratação de direito de uso de licenças do software AutoCAD.",
    "Aquisição de material de consumo de informática.",
    "Contratação de serviços de comunicação multimídia com tecnologia MPLS.",
])
def test_contexto_especifico_propoe_tic(objeto):
    registro = {
        "id_pncp": "1",
        "objeto": objeto,
        "fonte_original": "teste.json",
    }

    resultado = classificar_registro(registro)

    assert resultado["status"] == "tic_proposto"
    assert resultado["campo_evidencia"] == "objeto"
    assert resultado["evidencia"] == objeto
    assert resultado["evidencias_classificacao"]
    assert resultado["fonte"] == "teste.json"


@pytest.mark.parametrize("objeto", [
    "Aquisição de medicamentos por pregão eletrônico.",
    "Aquisição de limpeza para a rede municipal de saúde.",
    "Aquisição de cadeiras para a Secretaria de Tecnologia.",
    "Contratação de sistema de refrigeração.",
])
def test_termo_ambiguo_nao_classifica_automaticamente(objeto):
    resultado = classificar_registro({
        "id_pncp": "1",
        "objeto": objeto,
    })

    assert resultado["status"] != "tic_proposto"


def test_descricao_item_e_rastreada_sem_mutacao():
    registro = {
        "id_pncp": "1",
        "objeto": "Aquisição de equipamentos.",
        "descricao_item": "Servidor rack para armazenamento de dados.",
    }
    original = deepcopy(registro)

    resultado = classificar_registro(registro)

    assert resultado["status"] == "tic_proposto"
    assert resultado["campo_evidencia"] == "descricao_item"
    assert resultado["evidencia"] == registro["descricao_item"]
    assert registro == original


def test_nome_da_instituicao_nao_comprova_tic():
    resultado = classificar_registro({
        "id_pncp": "1",
        "objeto": "Contratação de jovem aprendiz.",
        "orgao": "Empresa Municipal de Informática",
    })

    assert resultado["status"] != "tic_proposto"


def test_objeto_misto_nao_e_forcado_para_servico():
    resultado = classificar_registro({
        "id_pncp": "1",
        "objeto": (
            "Aquisição de computadores e serviços de "
            "suporte técnico de informática."
        ),
    })

    assert resultado["status"] == "tic_proposto"
    assert resultado["tipo"] == "indeterminado"
