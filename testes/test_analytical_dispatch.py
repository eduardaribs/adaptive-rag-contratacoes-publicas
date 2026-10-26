import pytest

from app import analytical_dispatch as selecao
from app.interface_results import status_consulta, tabela_consulta


@pytest.fixture(autouse=True)
def configuracao(monkeypatch):
    monkeypatch.setenv("RAG_ANALYTICAL_ENABLED", "true")
    monkeypatch.setenv("RAG_DEMO_OFFLINE", "false")


@pytest.mark.parametrize("pergunta", [
    "No PE 038/26/2026, quantos itens foram homologados?",
    "Compare homologados e fracassados do PE 038/26/2026.",
    "Mostre uma tabela dos itens por situação no PE 038/26/2026.",
    "Qual é o valor estimado médio por item do PCA RJ 2026?",
])
def test_seleciona_consultas_analiticas(pergunta):
    assert selecao.deve_usar_analitica(pergunta, {})


@pytest.mark.parametrize("consulta", [
    {"is_refusal": True},
    {"plano": {"is_refusal": True}},
    {"estrategia": "recusa"},
    {"operacao": "resumir_itens_vinculos"},
    {"plano": {"operacao": "resumir_itens_vinculos"}},
])
def test_preserva_recusas_e_verificacao_de_vinculos(consulta):
    assert not selecao.deve_usar_analitica(
        "Quantos itens constam no PE 038/26/2026?", consulta
    )


def test_documental_segue_caminho_existente():
    assert not selecao.deve_usar_analitica(
        "Explique o pregão segundo a Lei 14.133.", {}
    )


def test_chave_desativada_preserva_fluxo_anterior(monkeypatch):
    monkeypatch.setenv("RAG_ANALYTICAL_ENABLED", "false")
    assert not selecao.deve_usar_analitica(
        "Quantos itens do PE 038/26/2026 foram homologados?", {}
    )


def test_demo_offline_nao_chama_caminho_real(monkeypatch):
    monkeypatch.setenv("RAG_DEMO_OFFLINE", "true")
    assert not selecao.deve_usar_analitica(
        "Quantos itens do PE 038/26/2026 foram homologados?", {}
    )


def test_preserva_ids_ao_chamar_adaptador(monkeypatch, tmp_path):
    from src import obs
    from app import analytical_adapter

    monkeypatch.setattr(obs, "PASTA_LOGS", tmp_path)
    chamadas = []

    def executar(pergunta, **kwargs):
        chamadas.append((pergunta, kwargs))
        return {"answer": "Resposta do adaptador", "run_id": kwargs["run_id"]}

    monkeypatch.setattr(
        analytical_adapter, "executar_analitica_interface", executar
    )
    r = selecao.tentar_analitica(
        "Quantos itens no PE 038/26/2026?",
        {"query_id": "q_preservada"},
        run_id="run_preservado",
    )
    assert r["answer"] == "Resposta do adaptador"
    assert chamadas[0][1]["query_id"] == "q_preservada"
    assert chamadas[0][1]["run_id"] == "run_preservado"


def test_status_e_tabela_aceitam_resultado_analitico():
    resultado = {
        "estrategia": "consulta_analitica",
        "run_id": "run_tela",
        "query_id": "q_tela",
        "campos": ["Situação", "Quantidade"],
        "registros": [{"Situação": "Homologado", "Quantidade": "8"}],
        "tokens": {"total": 15},
    }
    assert "Consulta analítica" in status_consulta(resultado)
    assert tabela_consulta(resultado) == {
        "headers": ["Situação", "Quantidade"],
        "data": [["Homologado", "8"]],
    }
