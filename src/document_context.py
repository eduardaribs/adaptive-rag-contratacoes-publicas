"""Seleção de parágrafos completos para contexto de PDFs conversacionais."""

import math
import os
import re
from collections import Counter

from src.context_focus import normalizar, termos


def preparar_contexto_pdf(evidencias, pergunta, montador, *, limite=None):
    evidencias = list(evidencias)
    if not evidencias or not all(
        evidencia.natureza == "conversacional"
        and (evidencia.source_file or "").lower().endswith(".pdf")
        for evidencia in evidencias
    ):
        return evidencias, []

    if limite is None:
        limite = int(os.getenv("DOCUMENT_CONTEXT_MAX_CHARS", "2500"))
    if type(limite) is not int or not 500 <= limite <= 12000:
        raise ValueError("Orçamento documental deve estar entre 500 e 12000.")

    if len(montador(evidencias)) <= limite:
        return evidencias, [
            {
                "chunk_id": e.chunk_id,
                "incluida_no_contexto": True,
                "caracteres_enviados": len(e.text),
                "selecao_documental": "texto completo dentro do orçamento",
            }
            for e in evidencias
        ]

    consulta = normalizar(pergunta)
    palavras_consulta = termos(pergunta)
    pede_empresa = bool(re.search(
        r"\bcontratada\b|\bfornecedor\b|\bempresa\b", consulta
    ))
    pede_objeto = bool(re.search(
        r"\bobjeto\b|\bprevisto\b|\baquisicao\b|"
        r"\bo que\b|\bdo que\b", consulta
    ))
    pede_comprovacao = bool(re.search(
        r"\bcomprova\w*\b|\bconfirm\w*\b|\bexistencia\b", consulta
    ))

    unidades = []
    for indice, evidencia in enumerate(evidencias):
        paragrafos = [
            texto.strip()
            for texto in re.split(r"\n[ \t]*\n+", evidencia.text)
            if texto.strip()
        ]
        for posicao, texto in enumerate(paragrafos):
            unidades.append({
                "evidencia": indice,
                "posicao": posicao,
                "texto": texto,
                "termos": termos(texto),
            })

    frequencias = Counter(
        palavra
        for unidade in unidades
        for palavra in unidade["termos"]
    )

    for unidade in unidades:
        texto = normalizar(unidade["texto"])
        pontuacao = sum(
            math.log(1 + len(unidades) / frequencias[palavra])
            for palavra in palavras_consulta & unidade["termos"]
        )

        # Prioridades de evidência, não respostas prontas.
        if pede_empresa and re.search(
            r"\bdoravante\s+denominada\s+contratada\b|"
            r"\bempresa\s+contratada\b|"
            r"\bfornecedor\s+registrado\b",
            texto,
        ):
            pontuacao += 20
        if pede_objeto and re.search(r"\btem\s+por\s+objeto\b", texto):
            pontuacao += 20
        if pede_comprovacao and re.search(
            r"\bsera\s+formalizada\b|\bsera\s+formalizado\b|"
            r"\bcomprovante\b|\batesto\b|\btermo\s+de\s+recebimento\b",
            texto,
        ):
            pontuacao += 8

        unidade["pontuacao"] = pontuacao

    ordem = sorted(
        range(len(unidades)),
        key=lambda i: (-unidades[i]["pontuacao"], i),
    )
    escolhidas = set()

    def reconstruir(indices):
        por_evidencia = {}
        for indice in sorted(indices):
            unidade = unidades[indice]
            por_evidencia.setdefault(unidade["evidencia"], []).append(
                unidade["texto"]
            )
        return [
            evidencias[indice].model_copy(update={
                "text": "\n\n".join(textos)
            })
            for indice, textos in sorted(por_evidencia.items())
        ]

    for indice in ordem:
        if unidades[indice]["pontuacao"] <= 0:
            continue
        tentativa = reconstruir(escolhidas | {indice})
        if len(montador(tentativa)) <= limite:
            escolhidas.add(indice)

    selecionadas = reconstruir(escolhidas)
    if not selecionadas:
        raise ValueError(
            "Nenhum parágrafo documental pertinente cabe inteiro "
            "no orçamento; não foi enviado texto cortado."
        )

    por_id = {e.chunk_id: e for e in selecionadas}
    detalhes = [
        {
            "chunk_id": evidencia.chunk_id,
            "incluida_no_contexto": evidencia.chunk_id in por_id,
            "caracteres_enviados": (
                len(por_id[evidencia.chunk_id].text)
                if evidencia.chunk_id in por_id else 0
            ),
            "selecao_documental": "parágrafos completos",
            "limite_contexto_caracteres": limite,
        }
        for evidencia in evidencias
    ]
    return selecionadas, detalhes
