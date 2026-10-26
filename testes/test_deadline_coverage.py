
from src.deadline_coverage import complementar_marco_prazo

PERGUNTA = "Qual prazo de entrega foi informado?"
RESPOSTA = "Papel em 10 dias e canetas em 15 dias. [Fonte: comunicacao_1]"


def evidencia(texto):
    return {
        "chunk_id": "comunicacao_1",
        "source_file": "comunicacao.txt",
        "text": texto,
    }


def test_complementa_apenas_com_trecho_literal_da_fonte_citada():
    fonte = evidencia("Canetas em 15 dias após a emissão do pedido.")
    saida = complementar_marco_prazo(PERGUNTA, RESPOSTA, [fonte])
    assert saida.startswith(RESPOSTA)
    assert "> após a emissão do pedido" in saida
    assert saida.endswith("[Fonte: comunicacao_1]")


def test_preserva_resposta_que_ja_informa_marco():
    resposta = "Entrega em 15 dias após a emissão do pedido. [Fonte: comunicacao_1]"
    assert complementar_marco_prazo(
        PERGUNTA, resposta,
        [evidencia("Entrega em 15 dias após a emissão do pedido.")],
    ) == resposta


def test_nao_inventa_marco_ausente():
    assert complementar_marco_prazo(
        PERGUNTA, RESPOSTA, [evidencia("Entrega em 15 dias.")]
    ) == RESPOSTA


def test_nao_usa_evidencia_nao_citada():
    fonte = evidencia("Entrega em 15 dias após a emissão do pedido.")
    fonte["chunk_id"] = "outra_comunicacao"
    assert complementar_marco_prazo(
        PERGUNTA, RESPOSTA, [fonte]
    ) == RESPOSTA


def test_nao_escolhe_entre_marcos_diferentes():
    fonte = evidencia(
        "Entrega em 15 dias após a emissão do pedido. "
        "Outra entrega em 10 dias a partir da assinatura do contrato."
    )
    assert complementar_marco_prazo(
        PERGUNTA, RESPOSTA, [fonte]
    ) == RESPOSTA


def test_nao_altera_pergunta_sobre_outro_assunto():
    assert complementar_marco_prazo(
        "Qual é o fornecedor?", RESPOSTA,
        [evidencia("Entrega em 15 dias após a emissão do pedido.")],
    ) == RESPOSTA
