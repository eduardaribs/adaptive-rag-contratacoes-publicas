
"""Complemento literal de marco inicial em respostas sobre entrega."""

import re


def complementar_marco_prazo(pergunta, resposta, evidencias):
    if not (
        re.search(r"\bprazos?\b", pergunta, re.IGNORECASE)
        and re.search(r"\bentregas?\b", pergunta, re.IGNORECASE)
        and re.search(r"\b\d+\s+dias\b", resposta, re.IGNORECASE)
    ):
        return resposta

    referencias = set(re.findall(
        r"\[Fonte:\s*([^\]]+)\]", resposta, re.IGNORECASE
    ))

    def campo(evidencia, nome):
        if isinstance(evidencia, dict):
            return evidencia.get(nome)
        return getattr(evidencia, nome, None)

    citadas = [
        e for e in evidencias
        if campo(e, "chunk_id") in referencias
        or campo(e, "source_file") in referencias
    ]
    if len(citadas) != 1:
        return resposta

    evidencia = citadas[0]
    texto = re.sub(r"\s+", " ", campo(evidencia, "text") or "")
    marcos = re.findall(
        r"\bdias(?:\s+[úu]teis)?\s+("
        r"ap[oó]s a emiss[aã]o do pedido"
        r"|ap[oó]s o recebimento da nota de empenho"
        r"|a partir da assinatura do contrato"
        r")\b",
        texto, re.IGNORECASE,
    )
    unicos = {marco.casefold(): marco for marco in marcos}
    if len(unicos) != 1:
        return resposta

    marco = next(iter(unicos.values()))
    if marco.casefold() in re.sub(r"\s+", " ", resposta).casefold():
        return resposta

    return (
        resposta.rstrip()
        + "\n\nMarco inicial citado na fonte:\n\n> "
        + marco
        + "\n\n[Fonte: "
        + campo(evidencia, "chunk_id")
        + "]"
    )
