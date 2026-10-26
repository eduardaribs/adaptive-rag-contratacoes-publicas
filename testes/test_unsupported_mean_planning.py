
import pytest

from src import router
from src.query_executor import executar_consulta


def analise(rotas):
    return {
        "query_id": "q_media_sem_suporte",
        "routes": rotas,
        "filters": {},
        "is_refusal": False,
        "refusal_reason": None,
    }


@pytest.mark.parametrize("pergunta", [
    "Qual foi o valor médio por quilo de arroz contratado pelos municípios?",
    "Informe o preço médio por litro de combustível nas compras.",
    "Calcule a média ponderada dos preços das contratações.",
    "Qual foi a média dos valores contratados?",
])
def test_media_sem_suporte_encerra_antes_da_recuperacao(
    pergunta, monkeypatch, tmp_path
):
    from src import obs
    monkeypatch.setattr(obs, "PASTA_LOGS", tmp_path)

    def proibido(*args, **kwargs):
        raise AssertionError("Não deve executar busca para cálculo sem suporte.")

    resultado = executar_consulta(
        pergunta,
        analise=analise(["agregada", "estruturada"]),
        recuperador=proibido,
        base=[],
    )
    assert resultado["executado"] is False
    assert resultado["plano"]["estrategia"] == "esclarecimento"
    assert resultado["plano"]["necessita_esclarecimento"] is True
    assert "ainda não está implementado" in resultado["mensagem"]


@pytest.mark.parametrize("pergunta", [
    "Explique o conceito de preço médio nas contratações.",
    "Como calcular a média ponderada dos preços?",
    "Qual é a definição de preço médio?",
])
def test_pergunta_explicativa_permanece_documental(pergunta):
    plano = router.planejar_consulta(
        pergunta, analise=analise(["normativa"])
    )
    assert plano["estrategia"] == "recuperacao_hibrida"
    assert plano["necessita_esclarecimento"] is False


@pytest.mark.parametrize("pergunta", [
    (
        "No PE 038/26/2026, quantos itens foram homologados, "
        "fracassados e desertos e qual foi a soma dos valores homologados?"
    ),
    (
        "Quantos itens constam no Plano de Contratações Anual do Estado "
        "do Rio de Janeiro para 2026 e qual é o valor total estimado informado?"
    ),
])
def test_resumos_implementados_permanecem_agregados(pergunta):
    plano = router.planejar_consulta(
        pergunta, analise=analise(["agregada"])
    )
    assert plano["estrategia"] == "consulta_agregada"
    assert plano["necessita_esclarecimento"] is False
