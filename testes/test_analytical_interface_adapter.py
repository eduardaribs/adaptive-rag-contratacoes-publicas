from copy import deepcopy

from app import analytical_adapter as adaptador


def preparar(monkeypatch, tmp_path, *, resultado=None, documental=None):
    monkeypatch.setattr(adaptador.obs, "PASTA_LOGS", tmp_path)
    plano = {
        "fonte": "itens_pe",
        "tarefas": [{
            "id": "t1",
            "operacao": "contar",
            "filtros": [],
            "agrupar_por": ["situacao_item"],
        }],
    }
    monkeypatch.setattr(
        adaptador, "interpretar_analitica",
        lambda *a, **k: {
            "tipo": "plano",
            "plano": deepcopy(plano),
            "pedido_documental": documental,
            "tokens": {"prompt": 10, "completion": 5, "total": 15},
        },
    )
    calculo = {
        "fonte": "itens_pe",
        "plano": plano,
        "resultados": [resultado or {
            "operacao": "contar",
            "campo": None,
            "agrupar_por": ["situacao_item"],
            "grupos": [
                {"situacao_item": "Homologado", "valor": 8},
                {"situacao_item": "Fracassado", "valor": 9},
                {"situacao_item": "Deserto", "valor": 2},
            ],
            "truncado": False,
        }],
        "comparacoes": [],
        "proveniencia": {
            "arquivo": "/arquivo/itens.csv",
            "sha256": "abc",
            "linhas_lidas": 19,
        },
    }
    monkeypatch.setattr(
        adaptador, "executar_fonte", lambda plano: deepcopy(calculo)
    )

    def geracao_proibida(*a, **k):
        raise AssertionError("Tabela não deve depender da geração.")
    monkeypatch.setattr(adaptador, "gerar_resposta", geracao_proibida)


def test_agrupamento_chega_no_contrato_da_tela(monkeypatch, tmp_path):
    preparar(monkeypatch, tmp_path)
    r = adaptador.executar_analitica_interface(
        "Tabela por situação", run_id="run_tabela", query_id="q_tabela"
    )
    assert r["executado"]
    assert r["campos"] == ["Situação", "Quantidade"]
    assert r["registros"][0] == {"Situação": "Homologado", "Quantidade": "8"}
    assert "| Fracassado | 9 |" in r["answer"]
    assert "[Fonte: resultado_calculado_run_tabela]" in r["answer"]
    assert r["fontes_recuperadas"] == []
    assert r["evidences"][0]["recuperado_do_indice"] is False
    assert r["tokens"]["total"] == 15


def test_listagem_preserva_ordem_e_limite(monkeypatch, tmp_path):
    preparar(monkeypatch, tmp_path, resultado={
        "operacao": "listar",
        "campos": ["numero_item", "valor_total_homologado"],
        "registros": [
            {"numero_item": "1", "valor_total_homologado": "44500.00"},
            {"numero_item": "3", "valor_total_homologado": "20646.00"},
        ],
        "total_registros": 8,
        "truncado": True,
    })
    r = adaptador.executar_analitica_interface("Liste os maiores itens")
    assert r["registros"][0]["numero_item"] == "1"
    assert r["registros"][1]["numero_item"] == "3"
    assert "Exibidos 2 de 8" in r["answer"]


def test_pedido_documental_nao_e_descartado(monkeypatch, tmp_path):
    preparar(monkeypatch, tmp_path, documental="Explique a regra da lei")

    def execucao_proibida(*a, **k):
        raise AssertionError("Não deve executar apenas parte da pergunta.")
    monkeypatch.setattr(adaptador, "executar_fonte", execucao_proibida)

    r = adaptador.executar_analitica_interface("Calcule e explique a lei")
    assert not r["executado"]
    assert r["necessita_esclarecimento"]
    assert "Explique a regra da lei" in r["answer"]


def test_esclarecimento_nao_calcula(monkeypatch, tmp_path):
    preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(
        adaptador, "interpretar_analitica",
        lambda *a, **k: {
            "tipo": "esclarecimento",
            "plano": None,
            "mensagem": "O arquivo não contém a data necessária.",
            "tokens": {"total": 0},
        },
    )

    def execucao_proibida(*a, **k):
        raise AssertionError("Esclarecimento não pode executar cálculo.")
    monkeypatch.setattr(adaptador, "executar_fonte", execucao_proibida)

    r = adaptador.executar_analitica_interface("Pergunta com dado ausente")
    assert not r["executado"]
    assert r["registros"] == []
    assert "data necessária" in r["answer"]
