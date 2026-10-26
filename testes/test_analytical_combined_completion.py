from app.analytical_combined import combinar_resultados


def analitico():
    return {
        "answer": "| Situação | Quantidade |\n| --- | --- |\n| Homologado | 8 |",
        "executado": True,
        "generation_available": False,
        "fontes_citadas": ["itens.csv"],
        "routes": ["agregada"],
    }


def documental():
    return {
        "answer": "Explicação documentada. [Fonte: lei_chunk_29]",
        "executado": True,
        "fontes_citadas": ["lei.html"],
        "routes": ["normativa"],
    }


def test_tabela_deterministica_e_documento_concluem_consulta():
    r = combinar_resultados(analitico(), documental(), "Explique a lei.")
    assert r["resposta_completa"] is True
    assert r["analitico_status"] == "respondida"
    assert r["documental_status"] == "respondida"


def test_falha_analitica_nao_e_ocultada_por_documento_valido():
    a = analitico()
    a.update({
        "answer": "Não foi possível apresentar a resposta gerada.",
        "fontes_citadas": [],
        "etapa_final": "validacao",
    })
    r = combinar_resultados(a, documental(), "Explique a lei.")
    assert r["resposta_completa"] is False
    assert r["analitico_status"] == "nao_concluida"
    assert r["documental_status"] == "respondida"
    assert "**Parte analítica não concluída**" in r["answer"]
    assert "Explicação documentada." in r["answer"]


def test_falha_documental_preserva_resultado_analitico():
    d = documental()
    d.update({
        "executado": False,
        "fontes_citadas": [],
        "answer": "Não foi possível concluir a parte documental.",
    })
    a = analitico()
    r = combinar_resultados(a, d, "Explique a lei.")
    assert r["resposta_completa"] is False
    assert r["analitico_status"] == "respondida"
    assert r["documental_status"] == "nao_concluida"
    assert a["answer"] in r["answer"]
