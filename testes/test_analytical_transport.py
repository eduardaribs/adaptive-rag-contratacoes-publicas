import json

import pytest
from pydantic import ValidationError

from src.analytical_transport import (
    Contar, Medir, decodificar_interpretacao,
)


def test_contagem_nao_expoe_parametros_de_listagem():
    campos = Contar.model_fields
    assert "campos" not in campos
    assert "ordenar_por" not in campos
    assert "campo" not in campos


@pytest.mark.parametrize("extra", [
    {"campos": ["numero_item"]},
    {"ordenar_por": "numero_item"},
    {"campo": "numero_item"},
])
def test_rejeita_opcoes_incompativeis_com_contagem(extra):
    with pytest.raises(ValidationError):
        Contar.model_validate({
            "id": "n", "operacao": "contar", **extra,
        })


def test_medida_exige_campo():
    with pytest.raises(ValidationError):
        Medir.model_validate({"id": "s", "operacao": "somar"})


@pytest.mark.parametrize("operacao,distintos", [
    ("contar_preenchidos", False),
    ("contar_distintos", True),
])
def test_converte_contagens_de_campo_sem_ambiguidade(operacao, distintos):
    dados = decodificar_interpretacao(json.dumps({
        "tipo": "plano", "mensagem": "", "pedido_documental": "",
        "plano": {
            "fonte": "itens_pe",
            "tarefas": [{
                "id": "n", "operacao": operacao, "campo": "fornecedor",
            }],
        },
    }))
    tarefa = dados["plano"]["tarefas"][0]
    assert tarefa["operacao"] == "contar"
    assert tarefa["distintos"] is distintos
    assert dados["pedido_documental"] is None
