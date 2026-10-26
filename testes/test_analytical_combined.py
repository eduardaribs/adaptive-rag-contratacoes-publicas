from copy import deepcopy

from app.analytical_combined import combinar_resultados


def analitico():
    return {
        "query": "Calcule e explique.",
        "run_id": "run_calculo",
        "query_id": "q_calculo",
        "executado": True,
        "answer": "Oito itens. [Fonte: calculo]",
        "routes": ["agregada"],
        "fontes": ["itens.csv"],
        "fontes_citadas": ["itens.csv"],
        "fontes_agregadas": ["itens.csv"],
        "evidences": [{"chunk_id": "calculo", "recuperado_do_indice": False}],
        "campos": ["Quantidade"],
        "registros": [{"Quantidade": "8"}],
        "calculo_analitico": {"resultado": 8},
        "tokens": {"total": 10},
        "plano": {"plano_analitico": {"fonte": "itens_pe"}},
    }


def documental():
    return {
        "run_id": "run_documental",
        "query_id": "q_documental",
        "answer": "Explicação. [Fonte: lei_chunk]",
        "executado": True,
        "routes": ["normativa"],
        "fontes": ["lei.html"],
        "fontes_recuperadas": ["lei.html"],
        "fontes_citadas": ["lei.html"],
        "evidences": [{"chunk_id": "lei_chunk"}],
        "tokens": {"total": 20},
    }


def test_preserva_calculo_tabela_fontes_e_ids():
    a, d = analitico(), documental()
    a_antes, d_antes = deepcopy(a), deepcopy(d)
    r = combinar_resultados(a, d, "Explique a regra")

    assert r["run_id"] == "run_calculo"
    assert r["query_id"] == "q_calculo"
    assert r["documental_run_id"] == "run_documental"
    assert r["documental_query_id"] == "q_documental"
    assert r["calculo_analitico"] == a["calculo_analitico"]
    assert r["registros"] == [{"Quantidade": "8"}]
    assert r["fontes_agregadas"] == ["itens.csv"]
    assert r["fontes_recuperadas"] == ["lei.html"]
    assert r["tokens"]["total"] == 30
    assert r["resposta_completa"] is True
    assert a == a_antes and d == d_antes


def test_documental_sem_fontes_nao_e_apresentado_como_completo():
    d = documental()
    d["fontes_citadas"] = []
    d["answer"] = "Falha na geração."
    r = combinar_resultados(analitico(), d, "Explique")
    assert r["resposta_completa"] is False
    assert "Parte documental não concluída" in r["answer"]
    assert r["calculo_analitico"]["resultado"] == 8


def test_recusa_documental_e_preservada():
    d = documental()
    d["is_refusal"] = True
    d["answer"] = "Não posso atender a essa parte."
    r = combinar_resultados(analitico(), d, "Pedido recusado")
    assert r["documental_status"] == "recusada"
    assert r["recusa_documental"] is True
    assert r["resposta_completa"] is False
    assert "Não posso atender" in r["answer"]
