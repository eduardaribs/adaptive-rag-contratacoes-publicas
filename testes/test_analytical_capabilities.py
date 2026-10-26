import json

import pytest

from src.analytical_capabilities import verificar_limites_conhecidos
from src import analytical_interpreter as interpretador


@pytest.mark.parametrize("pergunta", [
    "No PE 038/26/2026, quantos itens foram homologados?",
    "Compare homologados e fracassados do PE 038/26/2026.",
    "Qual é o valor total estimado médio por item do arquivo PCA "
    "disponibilizado para o RJ em 2026?",
    "Quantos itens do PE 038/26/2026 foram homologados antes de "
    "1 de março de 2026, considerando a data de homologação?",
    "Liste os itens do PE 038/26/2026 por valor total homologado.",
    "Quantos itens foram pagos no PE 999/26/2026?",
])
def test_nao_bloqueia_por_limite_de_outra_fonte(pergunta):
    assert verificar_limites_conhecidos(pergunta) is None


@pytest.mark.parametrize("pergunta,conceito", [
    (
        "Quantos itens do PE 038/26/2026 foram homologados "
        "antes da data de assinatura do contrato?",
        "assinatura",
    ),
    (
        "Qual é a soma dos valores homologados dos itens do "
        "PE 038/26/2026 que já foram pagos?",
        "pagamento",
    ),
    (
        "Quais itens do PE 038/26/2026 já foram entregues?",
        "entrega",
    ),
    (
        "Compare o valor estimado com o homologado no PE 038/26/2026.",
        "valor_estimado",
    ),
])
def test_identifica_limites_do_arquivo(pergunta, conceito):
    resultado = verificar_limites_conhecidos(pergunta)
    assert resultado["fonte"] == "itens_pe"
    assert conceito in {
        alerta["conceito"] for alerta in resultado["alertas"]
    }
    assert "outros documentos" in resultado["mensagem"]


def test_mencao_negativa_pede_esclarecimento_sem_inferir_intencao():
    resultado = verificar_limites_conhecidos(
        "No PE 038/26/2026, conte os homologados sem considerar pagamento."
    )
    assert resultado is not None
    assert "esclarecer" in resultado["mensagem"]


def test_interpretador_nao_chama_modelo_ao_encontrar_limite(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(interpretador.obs, "PASTA_LOGS", tmp_path)

    class ClienteProibido:
        @property
        def chat(self):
            raise AssertionError("O modelo não deveria ser chamado.")

    resultado = interpretador.interpretar_analitica(
        "Quantos itens do PE 038/26/2026 foram homologados "
        "antes da data de assinatura do contrato?",
        client=ClienteProibido(),
        run_id="run_limite_conhecido",
        query_id="q_limite_conhecido",
    )

    assert resultado["tipo"] == "esclarecimento"
    assert resultado["plano"] is None
    assert resultado["tentativas"] == 0
    assert resultado["tokens"]["total"] == 0

    eventos = [
        json.loads(linha)
        for arquivo in tmp_path.glob("pipeline-*.jsonl")
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    assert any(
        evento["run_id"] == "run_limite_conhecido"
        and evento["query_id"] == "q_limite_conhecido"
        and evento["stage"] == "validacao"
        and evento["input"]["tipo"] == "limites_conhecidos_fonte"
        for evento in eventos
    )
