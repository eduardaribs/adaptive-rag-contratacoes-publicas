"""Reconhecimento das formas gerais de pergunta normativa suportadas."""

import re

from src.document_scope import normalizar


def reconhecer_pedido_normativo(pergunta):
    texto = normalizar(pergunta or "")
    if re.search(r"\b(?:artigo|art\.|arts\.)\s*\d+", texto):
        return None

    padroes = [
        r"o que .+ estabelece sobre "
        r"(?:(?:o|a|os|as)\s+)?"
        r"([a-z]+(?:\s+[a-z]+){0,4})[?. ]*",

        r"explique as regras sobre "
        r"(?:(?:o|a|os|as)\s+)?"
        r"([a-z]+(?:\s+[a-z]+){0,4}?)"
        r"(?:\s+n[ao]\s+lei\b[^?]*)?[?. ]*",
    ]
    for padrao in padroes:
        pedido = re.fullmatch(padrao, texto)
        if pedido:
            return pedido
    return None
