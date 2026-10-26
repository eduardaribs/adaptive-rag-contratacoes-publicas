import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.analytical_plan import PlanoAnalitico


def test_erro_identifica_fonte_tarefa_e_campo_indisponivel():
    with pytest.raises(ValidationError) as erro:
        PlanoAnalitico.model_validate({
            "fonte": "itens_pe",
            "tarefas": [{
                "id": "t1", "operacao": "listar",
                "campos": ["numero_item", "descricao"],
            }],
        })
    mensagem = str(erro.value)
    assert "t1" in mensagem
    assert "itens_pe" in mensagem
    assert "descricao" in mensagem
    assert "Campos permitidos" in mensagem
    assert "numero_item" in mensagem


def test_descricao_permanece_disponivel_no_pca():
    plano = PlanoAnalitico.model_validate({
        "fonte": "pca",
        "tarefas": [{
            "id": "t1", "operacao": "listar",
            "campos": ["id_item", "descricao"],
        }],
    })
    assert plano.tarefas[0].campos == ["id_item", "descricao"]


def test_retentativa_recebe_o_campo_invalido_e_o_catalogo(
    monkeypatch, tmp_path
):
    from src import analytical_interpreter as modulo
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)

    def proposta(campos):
        return {
            "tipo": "plano", "mensagem": "", "pedido_documental": None,
            "plano": {
                "fonte": "itens_pe",
                "tarefas": [{
                    "id": "t1", "operacao": "listar",
                    "campos": campos, "distintos": False,
                    "filtros": [{
                        "campo": "situacao_item", "operador": "igual",
                        "valor": "homologado",
                    }],
                }],
            },
        }

    respostas = [
        proposta(["numero_item", "descricao"]),
        proposta(["numero_item"]),
    ]
    chamadas = []

    def criar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(
                    content=json.dumps(respostas[len(chamadas) - 1])
                ),
            )],
            usage=None,
        )

    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=criar)
    ))
    resultado = modulo.interpretar_analitica(
        "No PE 038/26/2026, quais itens foram homologados?",
        client=client, run_id="run_campos", query_id="q_campos",
    )
    assert len(chamadas) == 2
    retorno_validacao = chamadas[1]["messages"][-1]["content"]
    assert "descricao" in retorno_validacao
    assert "Campos permitidos" in retorno_validacao
    assert resultado["plano"]["tarefas"][0]["campos"] == ["numero_item"]
