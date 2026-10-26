import json
from types import SimpleNamespace

import pytest

from src import analytical_interpreter as modulo


def resposta_modelo(conteudo, finish_reason):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=conteudo),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )


def cliente_sequencial(respostas, chamadas):
    def criar(**kwargs):
        chamadas.append(kwargs)
        assert "response_format" not in kwargs
        return respostas[len(chamadas) - 1]

    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=criar)
        )
    )


def plano_valido():
    return json.dumps({
        "tipo": "plano",
        "mensagem": "",
        "pedido_documental": None,
        "plano": {
            "fonte": "itens_pe",
            "tarefas": [{
                "id": "t1",
                "operacao": "contar",
                "filtros": [{
                    "campo": "situacao_item",
                    "operador": "igual",
                    "valor": "homologado",
                }],
                "agrupar_por": [],
            }],
            "comparacoes": [],
            "formato": "texto",
            "pendencias": [],
        },
    })


def test_saida_incompleta_recebe_uma_correcao(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    chamadas = []
    cliente = cliente_sequencial([
        resposta_modelo('{"tipo":"plano",', "length"),
        resposta_modelo(plano_valido(), "stop"),
    ], chamadas)

    resultado = modulo.interpretar_analitica(
        "No PE 038/26/2026, quantos itens foram homologados? "
        "Responda em uma frase.",
        client=cliente,
        run_id="run_correcao_incompleta",
        query_id="q_correcao_incompleta",
    )

    assert len(chamadas) == 2
    assert resultado["tentativas"] == 2
    assert resultado["tipo"] == "plano"
    assert resultado["tokens"]["total"] == 30
    assert "não foi executado" in (
        chamadas[1]["messages"][-1]["content"]
    )

    eventos = [
        json.loads(linha)
        for caminho in tmp_path.glob("pipeline-*.jsonl")
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    assert any(
        evento["stage"] == "validacao"
        and evento["status"] == "erro"
        for evento in eventos
    )
    assert any(
        evento["stage"] == "validacao"
        and evento["status"] == "ok"
        for evento in eventos
    )


def test_duas_saidas_incompletas_permanecem_bloqueadas(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    chamadas = []
    cliente = cliente_sequencial([
        resposta_modelo('{"tipo":', "length"),
        resposta_modelo('{"tipo":', "length"),
    ], chamadas)

    with pytest.raises(ValueError, match="incompleto"):
        modulo.interpretar_analitica(
            "No PE 038/26/2026, quantos itens foram homologados?",
            client=cliente,
        )

    assert len(chamadas) == 2


def test_saida_vazia_pode_ser_corrigida(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    chamadas = []
    cliente = cliente_sequencial([
        resposta_modelo("", "stop"),
        resposta_modelo(plano_valido(), "stop"),
    ], chamadas)

    resultado = modulo.interpretar_analitica(
        "No PE 038/26/2026, quantos itens foram homologados?",
        client=cliente,
    )

    assert resultado["tipo"] == "plano"
    assert len(chamadas) == 2
