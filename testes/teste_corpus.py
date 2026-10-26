import json
from pathlib import Path

import pytest


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contratacoes_fixture.json"

@pytest.fixture
def contratacoes_fixture():
    with FIXTURE_PATH.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def test_fixture_possui_dez_registros(contratacoes_fixture):
    assert len(contratacoes_fixture) == 10


def test_chunk_possui_campos_obrigatorios(contratacoes_fixture):
    for chunk in contratacoes_fixture:
        assert chunk.get("chunk_id")
        assert chunk.get("text")
        assert isinstance(chunk.get("metadata"), dict)


def test_metadados_obrigatorios(contratacoes_fixture):
    obrigatorios = {
        "source_file",
        "doc_type",
        "sensitivity",
        "base_id",
        "natureza",
    }

    for chunk in contratacoes_fixture:
        metadata = chunk["metadata"]
        faltando = obrigatorios - set(metadata)

        assert not faltando, (
            f"{chunk.get('chunk_id')} sem metadados obrigatórios: {faltando}"
        )


def test_identificadores_unicos(contratacoes_fixture):
    chunk_ids = [chunk["chunk_id"] for chunk in contratacoes_fixture]
    controles = [
        chunk["metadata"]["numeroControlePNCP"]
        for chunk in contratacoes_fixture
    ]

    assert len(chunk_ids) == len(set(chunk_ids))
    assert len(controles) == len(set(controles))


def test_fixture_pertence_ao_rio_de_janeiro(contratacoes_fixture):
    for chunk in contratacoes_fixture:
        assert chunk["metadata"]["uf"] == "RJ"


def test_fixture_base_estruturada(contratacoes_fixture):
    for chunk in contratacoes_fixture:
        metadata = chunk["metadata"]

        assert metadata["base_id"] == "estruturada_pncp_rj"
        assert metadata["natureza"] == "estruturada"
        assert metadata["doc_type"] == "contratacao"


def test_modalidade_pregao_eletronico(contratacoes_fixture):
    for chunk in contratacoes_fixture:
        metadata = chunk["metadata"]

        assert metadata["modalidadeId"] == 6
        assert metadata["modalidadeNome"] == "Pregão - Eletrônico"


def test_sensitivity_definida(contratacoes_fixture):
    for chunk in contratacoes_fixture:
        assert chunk["metadata"]["sensitivity"]


def test_possui_objeto_da_compra(contratacoes_fixture):
    for chunk in contratacoes_fixture:
        assert chunk["metadata"]["objetoCompra"]


def test_possui_casos_com_valores_diferentes(contratacoes_fixture):
    valores = [
        chunk["metadata"]["valorTotalEstimado"]
        for chunk in contratacoes_fixture
        if chunk["metadata"]["valorTotalEstimado"] is not None
    ]

    assert valores
    assert min(valores) < max(valores)


def test_possui_caso_sem_valor_homologado(contratacoes_fixture):
    assert any(
        chunk["metadata"]["valorTotalHomologado"] is None
        for chunk in contratacoes_fixture
    )


def test_possui_caso_de_tecnologia(contratacoes_fixture):
    termos = ("software", "saas", "informática", "informatica")

    assert any(
        any(termo in chunk["metadata"]["objetoCompra"].lower() for termo in termos)
        for chunk in contratacoes_fixture
    )
