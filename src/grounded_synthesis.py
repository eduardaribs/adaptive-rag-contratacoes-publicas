"""Contrato sintático de síntese; não valida suporte semântico."""

import json
import re


INSTRUCOES_SINTESE = """

FORMATO DE TRANSPORTE OBRIGATÓRIO
Retorne somente JSON conforme o esquema solicitado.
Cada bloco contém:
- texto: uma explicação direta em português, sem citações embutidas;
- chunk_ids: IDs exatos dos trechos que sustentam esse texto.

As regras anteriores de precisão e sustentação continuam obrigatórias.
Neste formato, registre as referências em chunk_ids; o sistema acrescentará
[Fonte: ...] ao apresentar cada bloco. Não escreva esse marcador em texto.
Produza uma resposta explicativa, não uma seleção ou transcrição de trechos.
Responda somente aos pontos pedidos, preservando condições e exceções.
Divida afirmações com suportes diferentes em blocos separados.
Para perguntas com vários pontos, cubra cada ponto sustentado pelas evidências.
Se faltar informação, explicite a limitação dos trechos disponíveis e indique
os chunks examinados pertinentes. Não invente a informação ausente.
Não acrescente introduções ou conclusões genéricas.
"""


def esquema_sintese(ids):
    ids = list(dict.fromkeys(ids))
    if not ids or any(not isinstance(i, str) or not i.strip() for i in ids):
        raise ValueError("Síntese exige IDs de evidências válidos.")

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sintese_com_evidencias",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "blocos": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 12,
                        "items": {
                            "type": "object",
                            "properties": {
                                "texto": {"type": "string", "minLength": 1},
                                "chunk_ids": {
                                    "type": "array",
                                    "minItems": 1,
                                    "maxItems": len(ids),
                                    "items": {
                                        "type": "string",
                                        "enum": ids,
                                    },
                                },
                            },
                            "required": ["texto", "chunk_ids"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["blocos"],
                "additionalProperties": False,
            },
        },
    }


def renderizar_sintese(conteudo, ids):
    try:
        dados = json.loads(conteudo)
    except (TypeError, ValueError) as erro:
        raise ValueError("Síntese não contém JSON válido.") from erro

    if not isinstance(dados, dict) or set(dados) != {"blocos"}:
        raise ValueError("Estrutura de síntese inválida.")

    blocos = dados["blocos"]
    if not isinstance(blocos, list) or not 1 <= len(blocos) <= 12:
        raise ValueError("Quantidade de blocos inválida.")

    permitidos = set(ids)
    resposta = []

    for bloco in blocos:
        if not isinstance(bloco, dict) or set(bloco) != {"texto", "chunk_ids"}:
            raise ValueError("Bloco de síntese inválido.")

        texto = bloco["texto"]
        referencias = bloco["chunk_ids"]

        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("Bloco sem explicação.")
        if re.search(r"\[\s*Fonte\s*:", texto, flags=re.IGNORECASE):
            raise ValueError("Citação deve estar no campo chunk_ids.")
        if not isinstance(referencias, list) or not referencias:
            raise ValueError("Bloco sem referências.")
        if any(
            not isinstance(item, str) or item not in permitidos
            for item in referencias
        ):
            raise ValueError("Referência não pertence às evidências.")
        if len(set(referencias)) != len(referencias):
            raise ValueError("Referências duplicadas no bloco.")

        citacoes = " ".join(f"[Fonte: {item}]" for item in referencias)
        resposta.append(f"{texto.strip()} {citacoes}")

    return "\n\n".join(resposta)
