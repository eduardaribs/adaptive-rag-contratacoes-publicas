import json
from types import SimpleNamespace

import pytest

from src import analytical_interpreter as modulo


def cliente(dados, chamadas, finalizacao="stop"):
    def criar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason=finalizacao,
                message=SimpleNamespace(content=json.dumps(dados)),
            )],
            usage=None,
        )
    return SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=criar)
    ))


def entrada():
    return {
        "tipo": "plano",
        "mensagem": "",
        "pedido_documental": None,
        "plano": {
            "fonte": "itens_pe",
            "tarefas": [{"id": "total", "operacao": "contar"}],
        },
    }


def test_interpreta_e_registra_plano(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    chamadas = []
    r = modulo.interpretar_analitica(
        "Pergunta em linguagem natural.",
        client=cliente(entrada(), chamadas),
        run_id="run_teste", query_id="q_teste",
    )
    assert r["tipo"] == "plano"
    assert r["plano"]["tarefas"][0]["operacao"] == "contar"
    assert r["run_id"] == "run_teste"
    assert "response_format" not in chamadas[0]
    assert list(tmp_path.glob("pipeline-*.jsonl"))


def test_pedido_documental_nao_e_descartado(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    dados = entrada()
    dados["pedido_documental"] = "Explique a regra da norma."
    r = modulo.interpretar_analitica(
        "Conte e explique a regra.",
        client=cliente(dados, []),
    )
    assert r["pedido_documental"] == "explique a regra."


def test_esclarecimento_nao_produz_plano(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    dados = {
        "tipo": "esclarecimento",
        "mensagem": "O arquivo não contém data de assinatura.",
        "plano": None,
        "pedido_documental": None,
    }
    r = modulo.interpretar_analitica(
        "Filtre pela assinatura.", client=cliente(dados, [])
    )
    assert r["plano"] is None
    assert r["tipo"] == "esclarecimento"


@pytest.mark.parametrize("alterar", [
    lambda d: d.update(plano=None),
    lambda d: d["plano"].update(fonte="fonte_inventada"),
    lambda d: d["plano"]["tarefas"][0].update(operacao="executar_codigo"),
    lambda d: d["plano"].update(pendencias=["Falta um filtro"]),
])
def test_plano_invalido_nao_e_aceito(
    monkeypatch, tmp_path, alterar
):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    dados = entrada()
    alterar(dados)
    chamadas = []

    with pytest.raises(ValueError) as falha:
        modulo.interpretar_analitica(
            "Pergunta.", client=cliente(dados, chamadas)
        )

    assert "Stage inválido" not in str(falha.value)
    assert len(chamadas) == 2

    eventos = [
        json.loads(linha)
        for arquivo in tmp_path.glob("pipeline-*.jsonl")
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    roteamentos = [e for e in eventos if e["stage"] == "roteamento"]
    validacoes = [e for e in eventos if e["stage"] == "validacao"]

    assert len(roteamentos) == 2
    assert len(validacoes) == 2
    assert all(e["status"] == "ok" for e in roteamentos)
    assert all(e["status"] == "erro" for e in validacoes)
    assert all(
        e["input"]["tipo"] == "contrato_plano_analitico"
        for e in validacoes
    )
    assert all(
        "interpretacao_proposta" in e["output"]
        for e in roteamentos
    )


def test_planejamento_cortado_nao_e_aceito(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    with pytest.raises(ValueError, match="incompleto"):
        modulo.interpretar_analitica(
            "Pergunta.", client=cliente(entrada(), [], "length")
        )
