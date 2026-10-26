import pytest

from src.technology_classifier import classificar_registro


@pytest.mark.parametrize("objeto", [
    "Contratação para fornecimento em Software de como Serviço (SaaS).",
    "Fornecimento de link de internet dedicado ao datacenter.",
    "Prestação dos serviços de outsourcing de equipamentos de informática, "
    "com fornecimento de insumos.",
    "Contratação de serviços técnicos especializados de operação de "
    "infraestrutura de Tecnologia da Informação.",
    "Serviço Gerenciado de Segurança da Informação.",
])
def test_servicos_nao_viram_bens_por_fornecimento(objeto):
    resultado = classificar_registro({
        "id_pncp": "1",
        "objeto": objeto,
    })

    assert resultado["status"] == "tic_proposto"
    assert resultado["tipo"] == "servico_proposto"


def test_licenca_temporaria_nao_recebe_tipo_sem_evidencia():
    resultado = classificar_registro({
        "id_pncp": "1",
        "objeto": "Fornecimento de licenças de uso de software por 36 meses.",
    })

    assert resultado["status"] == "tic_proposto"
    assert resultado["tipo"] == "indeterminado"


def test_aquisicao_com_servicos_permanece_mista():
    resultado = classificar_registro({
        "id_pncp": "1",
        "objeto": (
            "Aquisição de computadores e prestação "
            "de serviços de suporte técnico de informática."
        ),
    })

    assert resultado["status"] == "tic_proposto"
    assert resultado["tipo"] == "indeterminado"


def test_aquisicao_de_solucao_com_instalacao_permanece_mista():
    resultado = classificar_registro({
        "id_pncp": "1",
        "objeto": (
            "Aquisição de solução de virtualização de mídias magnéticas "
            "para o Data Center, contemplando a contratação dos serviços "
            "de instalação e configuração."
        ),
    })

    assert resultado["status"] == "tic_proposto"
    assert resultado["tipo"] == "indeterminado"
