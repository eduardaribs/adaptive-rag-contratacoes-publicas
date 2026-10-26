"""Separação conservadora de pedidos analíticos e documentais explícitos."""

import re


def separar_pedidos(pergunta):
    """Preserva o prefixo analítico e o pedido documental identificado."""
    for encontrado in re.finditer(
        r"(?:\s+e\s+|;\s*|"
        r"[.!?]\s+(?:(?:depois|em seguida|al[eé]m disso|"
        r"tamb[eé]m)\s*[:,]?\s*)?)"
        r"(?P<documental>"
        r"(?:o\s+que\b"
        r"|(?:informe|mostre|apresente)\s+o\s+que\b"
        r"|explique\b|descreva\b|resuma\b|esclare[cç]a\b)"
        r".+)$",
        pergunta,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        documental = encontrado.group("documental").strip()
        if not re.search(
            r"\b(?:lei|decretos?|resolu[cç][oõ]es?|resolu[cç][aã]o|"
            r"portarias?|normas?|legisla[cç][aã]o|regras?|atas?|"
            r"artigos?|incisos?|comunica[cç][oõ]es|documentos?|"
            r"discutid[oa]s?)\b",
            documental,
            flags=re.IGNORECASE,
        ):
            continue

        analitica = pergunta[:encontrado.start()].strip().rstrip(";")
        if analitica:
            return {
                "analitica": analitica,
                "documental": documental,
            }

    return {"analitica": pergunta.strip(), "documental": None}


def extrair_pedido_documental(pergunta):
    """Compatibilidade com os consumidores anteriores."""
    return separar_pedidos(pergunta)["documental"]
