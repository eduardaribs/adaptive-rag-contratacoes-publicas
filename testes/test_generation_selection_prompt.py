from types import SimpleNamespace

from src import generate


def cliente_simulado(chamadas):
    def criar(**kwargs):
        chamadas.append(kwargs)
        if kwargs["response_format"]["json_schema"]["name"] == "selecao_evidencias":
            return "resposta_simulada"
        return SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content=(
                '{"blocos":[{"texto":"Prazos informados.",'
                '"chunk_ids":["documento_a"]}]}'
            )),
        )])

    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=criar)
        )
    )


def test_selecao_extrativa_utiliza_contrato_proprio():
    chamadas = []
    contexto = (
        "EVIDÊNCIA 1\n"
        "Chunk ID: documento.pdf_chunk_7\n"
        "Conteúdo: Objeto descrito no documento."
    )
    saida = generate.chamar_llm(
        pergunta="Qual é o objeto?",
        contexto=contexto,
        client=cliente_simulado(chamadas),
        modo_extrativo=True,
    )

    assert saida == "resposta_simulada"
    mensagens = chamadas[0]["messages"]
    assert mensagens[0]["content"] != generate.PROMPT_GERADOR
    assert "chunk_ids" in mensagens[0]["content"]
    assert "posições numéricas" in mensagens[0]["content"]
    assert contexto in mensagens[1]["content"]


def test_resposta_livre_preserva_prompt_e_contexto():
    chamadas = []
    generate.chamar_llm(
        pergunta="Quais são os prazos?",
        contexto="Chunk ID: documento_a\nConteúdo: Papel em dez dias; canetas em quinze dias.",
        client=cliente_simulado(chamadas),
    )

    mensagens = chamadas[0]["messages"]
    assert mensagens[0]["content"].startswith(generate.PROMPT_GERADOR)
    assert "Papel em dez dias" in mensagens[1]["content"]
    assert chamadas[0]["temperature"] == 0
