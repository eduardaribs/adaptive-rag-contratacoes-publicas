"""Cobertura de campos explícitos em atas com escopo identificado."""

import re

from src.document_scope import normalizar


def cobrir_campos_ata(
    pergunta, ranking, chunks_por_id, rotas, top_k, ids_escopo=None
):
    if (
        top_k <= 0
        or not ids_escopo
        or "conversacional" not in rotas
        or not re.search(r"\bata\b", normalizar(pergunta))
    ):
        return ranking

    consulta = normalizar(pergunta)
    elegiveis = [
        item for item in ranking
        if item["chunk_id"] in ids_escopo
    ]

    def texto(item):
        return normalizar(
            chunks_por_id.get(item["chunk_id"], {}).get("text", "")
        )

    def objeto(item):
        conteudo = texto(item)
        if "tem por objeto" in conteudo:
            return 400
        if re.search(r'"objetocompra"\s*:', conteudo):
            return 300
        return 0

    def pncp(item):
        conteudo = texto(item)
        return 400 if re.search(
            r'"(?:numerocontrolepncp|id_pncp)"\s*:\s*'
            r'"\d{14}-\d-\d{6}/\d{4}"',
            conteudo,
        ) else 0

    def contratada(item):
        conteudo = texto(item)
        if re.search(r"denominad[oa]\s+contratad[oa]\b", conteudo):
            return 400
        if "registrar os precos da empresa" in conteudo:
            return 300
        return 0

    requisitos = []
    if re.search(r"\bobjeto\b", consulta):
        requisitos.append(objeto)
    if re.search(r"\bpncp\b", consulta):
        requisitos.append(pncp)
    if re.search(r"\bfornecedor(?:es)?\b|\bcontratad[oa]\b", consulta):
        requisitos.append(contratada)

    obrigatorios = []
    for pontuar in requisitos:
        melhor = max(elegiveis, key=pontuar, default=None)
        if melhor is not None and pontuar(melhor) > 0:
            identificador = melhor["chunk_id"]
            if identificador not in obrigatorios:
                obrigatorios.append(identificador)

    # Não afirma cobrir mais campos do que o limite permite.
    if not obrigatorios or len(obrigatorios) > top_k:
        return ranking

    # Campos obrigatórios precisam preceder trechos genéricos:
    # a etapa multirrota ainda reservará vagas para outras naturezas.
    # Preserva scores e ordem RRF relativa dentro de cada grupo.
    ids_obrigatorios = set(obrigatorios)
    return (
        [item for item in ranking if item["chunk_id"] in ids_obrigatorios]
        + [item for item in ranking if item["chunk_id"] not in ids_obrigatorios]
    )
