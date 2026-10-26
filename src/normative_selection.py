"""Cobertura de definição em perguntas normativas gerais."""

import re

from src.document_scope import normalizar


from src.normative_query import reconhecer_pedido_normativo

def cobrir_definicao(pergunta, ranking, chunks_por_id, rotas, top_k):
    """Reserva uma vaga, sem alterar scores nem acrescentar candidatos."""
    if set(rotas) != {"normativa"} or top_k < 2:
        return ranking

    texto = normalizar(pergunta)
    if re.search(r"\b(?:artigo|art\.|arts\.)\s*\d+", texto):
        return ranking

    pedido = reconhecer_pedido_normativo(texto)
    if not pedido:
        return ranking

    assunto = pedido.group(1).strip()
    padrao = re.compile(
        r"(?<!\w)" + re.escape(assunto) + r"\s*:"
    )

    definicao = next(
        (
            item for item in ranking
            if padrao.search(normalizar(
                chunks_por_id.get(item["chunk_id"], {}).get("text", "")
            ))
        ),
        None,
    )
    if definicao is None:
        return ranking

    selecionados = ranking[:top_k]
    if any(
        item["chunk_id"] == definicao["chunk_id"]
        for item in selecionados
    ):
        return ranking

    ids = {
        item["chunk_id"] for item in ranking[:top_k - 1]
    } | {definicao["chunk_id"]}

    # Mantém a ordem relativa dentro de cada grupo.
    return (
        [item for item in ranking if item["chunk_id"] in ids]
        + [item for item in ranking if item["chunk_id"] not in ids]
    )

def cobrir_selecao_definicao(pergunta, conteudo, evidencias, rotas):
    """
    Complementa uma seleção extrativa já válida quando faltam
    evidências explícitas necessárias para cobrir a pergunta.

    Mantém a cobertura normativa existente e também cobre campos
    factuais objetivos, como objeto, número de controle PNCP
    e fornecedor/contratada.
    """
    import json
    from src.grounded_quotes import preparar_selecao_extrativa

    # Primeiro valida a saída original do modelo.
    # Se o JSON for inválido, chunk inexistente etc., continua falhando
    # normalmente no guardrail.
    preparar_selecao_extrativa(conteudo, evidencias)

    selecionados = list(
        dict.fromkeys(json.loads(conteudo)["chunk_ids"])
    )

    por_id = {
        evidencia.chunk_id: evidencia
        for evidencia in evidencias
    }

    texto_pergunta = normalizar(pergunta)

    # ========================================================
    # Cobertura normativa já existente
    # ========================================================

    if (
        set(rotas) == {"normativa"}
        and all(
            evidencia.natureza == "normativa"
            for evidencia in evidencias
        )
    ):
        if re.search(
            r"\b(?:artigo|art\.|arts\.)\s*\d+",
            texto_pergunta,
        ):
            return conteudo

        pedido = reconhecer_pedido_normativo(texto_pergunta)

        if not pedido:
            return conteudo

        padrao = re.compile(
            r"(?<!\w)"
            + re.escape(pedido.group(1).strip())
            + r"\s*:"
        )

        ajustados = _cobrir_artigos_do_assunto(
            pedido.group(1).strip(), selecionados, evidencias
        )
        if ajustados != selecionados:
            selecionados = ajustados
            conteudo = json.dumps(
                {"chunk_ids": selecionados}, ensure_ascii=False
            )

        # Mantém a escolha quando a definição já foi selecionada.
        if any(
            identificador in por_id
            and padrao.search(
                normalizar(por_id[identificador].text)
            )
            for identificador in selecionados
        ):
            return conteudo

        definicao = next(
            (
                evidencia
                for evidencia in evidencias
                if padrao.search(
                    normalizar(evidencia.text)
                )
            ),
            None,
        )

        if definicao is None:
            return conteudo

        ids = selecionados[:4] + [definicao.chunk_id]

        return json.dumps(
            {"chunk_ids": list(dict.fromkeys(ids))},
            ensure_ascii=False,
        )

    # ========================================================
    # Cobertura factual para atas / contratações
    # ========================================================

    def texto_bruto(evidencia):
        return evidencia.text.casefold()

    def texto_normalizado(evidencia):
        return normalizar(evidencia.text)

    # --------------------------------------------------------
    # OBJETO
    # --------------------------------------------------------

    def score_objeto(evidencia):
        bruto = texto_bruto(evidencia)
        normalizado = texto_normalizado(evidencia)

        score = 0

        # JSON estruturado do PNCP
        if "objetocompra" in re.sub(
            r"[^a-z0-9]",
            "",
            bruto,
        ):
            score += 300

        # Formulação explícita típica de atas
        if "tem por objeto" in normalizado:
            score += 300

        if "a presente ata tem por objeto" in normalizado:
            score += 100

        return score

    # --------------------------------------------------------
    # NÚMERO DE CONTROLE PNCP
    # --------------------------------------------------------

    def score_pncp(evidencia):
        bruto = texto_bruto(evidencia)
        normalizado = texto_normalizado(evidencia)

        compacto = re.sub(
            r"[^a-z0-9]",
            "",
            bruto,
        )

        score = 0

        if "numerocontrolepncp" in compacto:
            score += 400

        if "numero de controle pncp" in normalizado:
            score += 350

        # Menção genérica ao PNCP não é suficiente.
        return score

    # --------------------------------------------------------
    # FORNECEDOR / CONTRATADA
    # --------------------------------------------------------

    def score_fornecedor(evidencia):
        normalizado = texto_normalizado(evidencia)

        score = 0

        if "doravante denominada contratada" in normalizado:
            score += 400

        if "doravante denominado contratado" in normalizado:
            score += 400

        if "resolve registrar os precos da empresa" in normalizado:
            score += 250

        if "fornecedor registrado" in normalizado:
            score += 60

        # Evita confundir fabricante/marca do produto
        # com a empresa fornecedora.
        if (
            "fabricante" in normalizado
            and "contratada" not in normalizado
            and "registrar os precos da empresa"
            not in normalizado
        ):
            score -= 300

        return score

    requisitos = []

    if re.search(r"\bobjeto\b", texto_pergunta):
        requisitos.append(score_objeto)

    if (
        "pncp" in texto_pergunta
        and (
            "numero de controle" in texto_pergunta
            or "controle pncp" in texto_pergunta
            or "numero pncp" in texto_pergunta
        )
    ):
        requisitos.append(score_pncp)

    if re.search(
        r"\bfornecedor(?:es)?\b|\bcontratad[oa]\b",
        texto_pergunta,
    ):
        requisitos.append(score_fornecedor)

    if not requisitos:
        return conteudo

    faltantes = []

    for pontuador in requisitos:

        # Campo já coberto pela seleção original.
        if any(
            identificador in por_id
            and pontuador(por_id[identificador]) > 0
            for identificador in selecionados
        ):
            continue

        candidatos = [
            (
                pontuador(evidencia),
                evidencia,
            )
            for evidencia in evidencias
        ]

        candidatos = [
            item
            for item in candidatos
            if item[0] > 0
        ]

        if not candidatos:
            continue

        candidatos.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        melhor = candidatos[0][1]

        if (
            melhor.chunk_id not in selecionados
            and melhor.chunk_id not in faltantes
        ):
            faltantes.append(melhor.chunk_id)

    if not faltantes:
        return conteudo

    # Mantém no máximo cinco chunks.
    #
    # Se o modelo já tiver escolhido cinco, reserva as últimas
    # vagas para as evidências necessárias à cobertura da pergunta.
    quantidade_modelo = max(
        0,
        5 - len(faltantes),
    )

    ids = (
        selecionados[:quantidade_modelo]
        + faltantes
    )

    ids = list(dict.fromkeys(ids))[:5]

    return json.dumps(
        {"chunk_ids": ids},
        ensure_ascii=False,
    )
    import json
    from src.grounded_quotes import preparar_selecao_extrativa

    preparar_selecao_extrativa(conteudo, evidencias)
    selecionados = list(dict.fromkeys(json.loads(conteudo)["chunk_ids"]))

    if (
        set(rotas) != {"normativa"}
        or not all(e.natureza == "normativa" for e in evidencias)
    ):
        return conteudo

    texto = normalizar(pergunta)
    if re.search(r"\b(?:artigo|art\.|arts\.)\s*\d+", texto):
        return conteudo

    pedido = reconhecer_pedido_normativo(texto)
    if not pedido:
        return conteudo

    padrao = re.compile(
        r"(?<!\w)" + re.escape(pedido.group(1).strip()) + r"\s*:"
    )

    # Mantém a escolha do modelo quando ele já selecionou uma definição.
    por_id = {e.chunk_id: e for e in evidencias}
    if any(
        padrao.search(normalizar(por_id[i].text))
        for i in selecionados
    ):
        return conteudo

    definicao = next(
        (e for e in evidencias if padrao.search(normalizar(e.text))),
        None,
    )
    if definicao is None:
        return conteudo

    # Reserva a última vaga quando o limite de cinco já foi atingido.
    ids = selecionados[:4] + [definicao.chunk_id]
    return json.dumps({"chunk_ids": ids}, ensure_ascii=False)


def _cobrir_artigos_do_assunto(assunto, selecionados, evidencias):
    """Cobre artigos recuperados que mencionam explicitamente o assunto."""
    padrao = re.compile(
        r"(?<!\w)" + re.escape(assunto) + r"(?!\w)"
    )
    por_id = {e.chunk_id: e for e in evidencias}

    def artigo(e):
        return bool(re.match(
            r"^\s*art\.?\s*\d+", normalizar(e.text)
        ))

    def menciona(e):
        return bool(padrao.search(normalizar(e.text)))

    pertinentes = [
        e.chunk_id for e in evidencias
        if artigo(e) and menciona(e)
    ]
    if not pertinentes:
        return selecionados

    # Não descarta evidências sem estrutura de artigo reconhecida.
    mantidos = [
        identificador for identificador in selecionados
        if not artigo(por_id[identificador])
        or menciona(por_id[identificador])
    ]
    faltantes = [
        identificador for identificador in pertinentes
        if identificador not in mantidos
    ]
    vagas = max(0, 5 - len(faltantes))
    return list(dict.fromkeys(mantidos[:vagas] + faltantes))[:5]
