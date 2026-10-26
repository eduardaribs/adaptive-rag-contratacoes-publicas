"""Orçamento de contexto normativo; não altera corpus nem índice."""

import os

from src.context_focus import termos


def limitar_contexto_normativo(
    evidencias, pergunta, montador, *, limite=None
):
    evidencias = list(evidencias)
    if not evidencias or not all(
        evidencia.natureza == "normativa" for evidencia in evidencias
    ):
        return evidencias, []

    if limite is None:
        limite = int(os.getenv("NORMATIVE_CONTEXT_MAX_CHARS", "6000"))
    if isinstance(limite, bool) or not isinstance(limite, int):
        raise ValueError("Orçamento de contexto deve ser inteiro.")
    if not 500 <= limite <= 12000:
        raise ValueError("Orçamento normativo deve estar entre 500 e 12000.")

    consulta = termos(pergunta)
    pontuacoes = [
        len(consulta & termos(evidencia.text))
        / max(1, len(evidencia.text))
        for evidencia in evidencias
    ]

    # Heurística lexical, não uma avaliação semântica.
    # Empates preservam a posição original da recuperação.
    ordem = sorted(
        range(len(evidencias)),
        key=lambda indice: (-pontuacoes[indice], indice),
    )

    selecionadas = []
    incluidos = set()
    for indice in ordem:
        candidata = evidencias[indice]
        if len(montador(selecionadas + [candidata])) <= limite:
            selecionadas.append(candidata)
            incluidos.add(indice)

    if not selecionadas:
        raise ValueError(
            "Nenhuma evidência normativa cabe inteira no orçamento "
            "de contexto. Não foi enviado um trecho cortado."
        )

    detalhes = [
        {
            "chunk_id": evidencia.chunk_id,
            "incluida_no_contexto": indice in incluidos,
            "caracteres_enviados": (
                len(evidencia.text) if indice in incluidos else 0
            ),
            "prioridade_lexical_por_caractere": pontuacoes[indice],
            "limite_contexto_caracteres": limite,
            "motivo_orcamento": (
                "incluída inteira após o foco"
                if indice in incluidos
                else "não cabe inteira no orçamento"
            ),
        }
        for indice, evidencia in enumerate(evidencias)
    ]
    return selecionadas, detalhes
