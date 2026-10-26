import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src import analytical_interpreter as modulo


def test_modelo_nao_recebe_filtros_globais(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    chamadas = []

    def criar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=json.dumps({
                    "tipo": "plano",
                    "mensagem": "",
                    "pedido_documental": None,
                    "plano": {
                        "fonte": "itens_pe",
                        "tarefas": [{
                            "id": "h",
                            "operacao": "contar",
                            "filtros": [{
                                "campo": "situacao_item",
                                "operador": "igual",
                                "valor": "homologado",
                            }],
                        }],
                    },
                })),
            )],
            usage=None,
        )

    cliente = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=criar)
    ))
    resultado = modulo.interpretar_analitica(
        "Conte os itens homologados.",
        client=cliente,
    )

    assert "response_format" not in chamadas[0]
    assert "Conte os itens homologados." in (
        chamadas[0]["messages"][1]["content"]
    )
    assert "CATÁLOGO:" in chamadas[0]["messages"][1]["content"]
    assert resultado["plano"]["filtros"] == []
    assert resultado["plano"]["tarefas"][0]["filtros"]


def test_rejeita_filtros_globais_retornados_fora_do_schema():
    with pytest.raises(ValidationError, match="dentro de cada tarefa"):
        modulo.InterpretacaoAnalitica.model_validate({
            "tipo": "plano",
            "mensagem": "",
            "pedido_documental": None,
            "plano": {
                "fonte": "itens_pe",
                "filtros": [{
                    "campo": "situacao_item",
                    "operador": "igual",
                    "valor": "homologado",
                }],
                "tarefas": [{"id": "n", "operacao": "contar"}],
            },
        })
