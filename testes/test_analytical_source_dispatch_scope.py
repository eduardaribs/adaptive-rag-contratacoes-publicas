import pytest

from app import analytical_dispatch as modulo


@pytest.fixture(autouse=True)
def configurar(monkeypatch):
    monkeypatch.setenv("RAG_ANALYTICAL_ENABLED", "true")
    monkeypatch.setenv("RAG_DEMO_OFFLINE", "false")


@pytest.mark.parametrize("pergunta", [
    "Qual foi o valor médio por quilo de arroz contratado "
    "por municípios do RJ em 2025, e em quais modalidades?",
    "Quais contratos de licenciamento de software foram assinados "
    "por órgãos estaduais do RJ acima de R$ 500 mil em 2025, "
    "e quais foram os fornecedores?",
    "Quais itens foram homologados no PE 039/26/2026?",
])
def test_rota_agregada_nao_autoriza_arquivo_sem_vinculo(
    monkeypatch, pergunta
):
    from app import analytical_adapter

    def proibido(*args, **kwargs):
        raise AssertionError("Executor chamado para fonte não identificada.")

    monkeypatch.setattr(
        analytical_adapter, "executar_analitica_interface", proibido
    )
    consulta = {
        "routes": ["agregada"],
        "plano": {"bases": ["agregada"]},
        "query_id": "q_escopo",
    }
    assert not modulo.deve_usar_analitica(pergunta, consulta)
    assert modulo.tentar_analitica(
        pergunta, consulta, run_id="run_escopo"
    ) is None


@pytest.mark.parametrize("pergunta", [
    "Relacione os itens homologados do PE 038/26/2026.",
    "Quais fornecedores tiveram itens homologados no PE 038/26/2026?",
    "Quais categorias aparecem no PCA disponibilizado para o RJ em 2026?",
])
def test_fonte_reconhecida_preserva_reformulacoes(pergunta):
    assert modulo.deve_usar_analitica(pergunta, {})
