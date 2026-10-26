from types import SimpleNamespace

from src import generate


def cliente(chamadas):
    def criar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content=(
                '{"blocos":[{"texto":"Prazo informado.",'
                '"chunk_ids":["documento_a"]}]}'
            )),
        )])
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=criar)
        )
    )


def test_extrativo_restringe_formato_e_ids_do_contexto():
    chamadas = []
    generate.chamar_llm(
        pergunta="Qual é o objeto?",
        contexto=(
            "EVIDÊNCIA 1\nChunk ID: documento_a\nConteúdo: Texto A.\n"
            "EVIDÊNCIA 2\nChunk ID: documento_b\nConteúdo: Texto B."
        ),
        client=cliente(chamadas),
        modo_extrativo=True,
    )
    formato = chamadas[0]["response_format"]
    assert formato["type"] == "json_schema"
    esquema = formato["json_schema"]["schema"]
    assert esquema["required"] == ["chunk_ids"]
    assert esquema["additionalProperties"] is False
    assert esquema["properties"]["chunk_ids"]["items"]["enum"] == [
        "documento_a", "documento_b"
    ]
    assert esquema["properties"]["chunk_ids"]["minItems"] == 0


def test_sintese_recebe_schema_distinto_da_selecao():
    chamadas = []
    generate.chamar_llm(
        pergunta="Quais são os prazos?",
        contexto="Chunk ID: documento_a\nConteúdo: Papel em dez dias.",
        client=cliente(chamadas),
    )
    formato = chamadas[0]["response_format"]
    assert formato["json_schema"]["name"] == "sintese_com_evidencias"
