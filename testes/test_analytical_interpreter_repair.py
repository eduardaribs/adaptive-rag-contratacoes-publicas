import json
from types import SimpleNamespace

from src import analytical_interpreter as modulo


def test_corrige_plano_com_feedback_sem_executar_dados(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    chamadas = []

    def filtro(valor):
        return {"campo": "situacao_item", "operador": "igual", "valor": valor}

    invalido = {
        "tipo": "plano", "mensagem": "", "pedido_documental": None,
        "plano": {
            "fonte": "itens_pe",
            "tarefas": [{
                "id": "grupo", "operacao": "contar",
                "filtros": [filtro("homologado"), filtro("fracassado")],
            }],
        },
    }
    valido = {
        "tipo": "plano", "mensagem": "", "pedido_documental": None,
        "plano": {
            "fonte": "itens_pe",
            "tarefas": [
                {"id": "h", "operacao": "contar",
                 "filtros": [filtro("homologado")]},
                {"id": "f", "operacao": "contar",
                 "filtros": [filtro("fracassado")]},
            ],
            "comparacoes": [{
                "id": "d", "operacao": "diferenca",
                "esquerda": "h", "direita": "f",
            }],
        },
    }

    respostas = iter([invalido, valido])

    def criar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=json.dumps(next(respostas))),
            )],
            usage=SimpleNamespace(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            ),
        )

    cliente = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=criar)
    ))
    resultado = modulo.interpretar_analitica(
        "Compare os grupos.",
        client=cliente,
    )

    assert len(chamadas) == 2
    assert resultado["tentativas"] == 2
    assert resultado["tokens"]["total"] == 30
    assert len(resultado["plano"]["tarefas"]) == 2
    assert "contraditórios" in chamadas[1]["messages"][-1]["content"]
    assert chamadas[1]["messages"][-2]["role"] == "assistant"
    assert len(chamadas[0]["messages"]) == 2
