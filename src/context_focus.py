"""Seleciona incisos completos para o contexto, sem alterar o corpus."""

import re
import unicodedata
import math
from collections import Counter

STOP = set("""
a ao aos as o os de da das do dos e em no nos na nas um uma
que qual quais como quando onde por para com se segundo sobre
explique explicar informe informar estabelece ser deve utilizado
lei artigo art nº n é são está estão sendo sua seu suas seus
""".split())

def normalizar(texto):
    return "".join(
        letra for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )

def termos(texto):
    return {
        palavra
        for palavra in re.findall(r"[a-z]+", normalizar(texto))
        if len(palavra) > 2 and palavra not in STOP
    }

def focar_evidencias(evidencias, pergunta):
    consulta = termos(pergunta)

    # Referências a incisos em outros trechos são preservadas.
    referencias = set()
    for evidencia in evidencias:
        referencias.update(re.findall(
            r"\binciso\s+([IVXLCDM]+)\b",
            evidencia.text,
            flags=re.IGNORECASE,
        ))
    referencias = {item.upper() for item in referencias}

    resultado = []
    detalhes = []

    for evidencia in evidencias:
        original = evidencia.text

        # Separa incisos completos, mantendo suas alíneas e condições.
        marcadores = list(re.finditer(
            r"(?m)^[ \t]*([IVXLCDM]+)\s*[-–]\s*",
            original,
        ))

        if evidencia.natureza == "normativa" and len(original) > 6000 and len(marcadores) >= 5:
            unidades = []
            for indice, marcador in enumerate(marcadores):
                fim = (
                    marcadores[indice + 1].start()
                    if indice + 1 < len(marcadores)
                    else len(original)
                )
                unidades.append((
                    marcador.group(1),
                    original[marcador.start():fim].strip(),
                ))

            palavras = [termos(texto) for _, texto in unidades]
            frequencias = Counter(
                palavra for conjunto in palavras for palavra in conjunto
            )

            pontuacoes = [
                sum(
                    math.log(1 + len(unidades) / frequencias[palavra])
                    for palavra in consulta & conjunto
                )
                for conjunto in palavras
            ]

            melhores = sorted(
                range(len(unidades)),
                key=lambda i: (-pontuacoes[i], i),
            )
            selecionados = {
                i for i in melhores[:3] if pontuacoes[i] > 0
            }
            selecionados.update(
                i for i, (inciso, _) in enumerate(unidades)
                if inciso in referencias
            )

            if selecionados:
                cabecalho = original[:marcadores[0].start()].strip()
                texto = cabecalho + "\n\n" + "\n\n".join(
                    unidades[i][1] for i in sorted(selecionados)
                )
            else:
                texto = original
        else:
            texto = original

        resultado.append(evidencia.model_copy(update={"text": texto}))
        detalhes.append({
            "chunk_id": evidencia.chunk_id,
            "caracteres_originais": len(original),
            "caracteres_enviados": len(texto),
        })

    return resultado, detalhes
