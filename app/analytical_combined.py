"""Combina cálculo e documentos sem recalcular nem misturar suas fontes."""

from copy import deepcopy


def combinar_resultados(analitico, documental, pedido_documental):
    saida = deepcopy(analitico)

    # Cálculo executado não significa resposta analítica concluída.
    # Tabelas determinísticas são válidas sem chamada ao gerador.
    analitica_concluida = bool(
        analitico.get("executado")
        and analitico.get("answer")
        and analitico.get("fontes_citadas")
        and not analitico.get("is_refusal")
        and not analitico.get("necessita_esclarecimento")
        and analitico.get("etapa_final") in (None, "geracao")
    )
    titulo_analitico = (
        "**Resultado calculado sobre o arquivo**"
        if analitica_concluida
        else "**Parte analítica não concluída**"
    )

    if documental.get("is_refusal"):
        status = "recusada"
    elif (
        documental.get("executado")
        and documental.get("fontes_citadas")
        and not documental.get("necessita_esclarecimento")
    ):
        status = "respondida"
    else:
        status = "nao_concluida"

    resposta_documental = documental.get("answer") or (
        "Não foi possível concluir a parte documental."
    )
    titulo = (
        "**Resposta baseada nos documentos**"
        if status == "respondida"
        else "**Parte documental não concluída**"
    )

    saida.update({
        "estrategia": "combinada_analitica",
        "resposta_analitica": analitico["answer"],
        "resposta_documental": resposta_documental,
        "pedido_documental": pedido_documental,
        "documental_query_id": documental.get("query_id"),
        "documental_run_id": documental.get("run_id"),
        "documental_status": status,
        "recusa_documental": bool(documental.get("is_refusal")),
        "analitico_status": (
            "respondida" if analitica_concluida else "nao_concluida"
        ),
        "resposta_completa": (
            analitica_concluida and status == "respondida"
        ),
        "answer": (
            titulo_analitico + "\n\n"
            + analitico["answer"]
            + "\n\n" + titulo + "\n\n"
            + resposta_documental
        ),
        "routes": sorted(set(
            analitico.get("routes", [])
            + documental.get("routes", [])
        )),
        "fontes": sorted(set(
            analitico.get("fontes", [])
            + documental.get("fontes", [])
        )),
        "fontes_recuperadas": list(
            documental.get("fontes_recuperadas", [])
        ),
        "fontes_citadas": sorted(set(
            analitico.get("fontes_citadas", [])
            + documental.get("fontes_citadas", [])
        )),
        "evidences": (
            deepcopy(analitico.get("evidences", []))
            + deepcopy(documental.get("evidences", []))
        ),
    })

    saida["plano"] = {
        **deepcopy(analitico.get("plano", {})),
        "estrategia": "combinada_analitica",
        "bases": saida["routes"],
        "pedido_documental": pedido_documental,
        "plano_documental": deepcopy(documental.get("plano", {})),
    }

    saida["tokens"] = {
        chave: (
            (analitico.get("tokens") or {}).get(chave, 0)
            + (documental.get("tokens") or {}).get(chave, 0)
        )
        for chave in ("prompt", "completion", "total")
    }
    return saida
