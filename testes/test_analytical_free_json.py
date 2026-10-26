import json

import pytest
from pydantic import ValidationError

from src.analytical_transport import decodificar_interpretacao


def exemplo():
    return {
        "tipo": "plano",
        "mensagem": "",
        "pedido_documental": None,
        "plano": {
            "fonte": "itens_pe",
            "tarefas": [{"id": "n", "operacao": "contar"}],
        },
    }


@pytest.mark.parametrize("abertura", ["```json", "```"])
def test_aceita_apenas_invólucro_json(abertura):
    texto = abertura + "\n" + json.dumps(exemplo()) + "\n```"
    resultado = decodificar_interpretacao(texto)
    assert resultado["plano"]["tarefas"][0]["operacao"] == "contar"


def test_json_livre_continua_rejeitando_campos_incompativeis():
    dados = exemplo()
    dados["plano"]["tarefas"][0]["ordenar_por"] = "numero_item"
    with pytest.raises(ValidationError):
        decodificar_interpretacao(json.dumps(dados))


@pytest.mark.parametrize("texto", [
    "Uma resposta em prosa.",
    '```python\n{"tipo": "plano"}\n```',
    '{"tipo": "plano"} texto adicional',
])
def test_rejeita_conteudo_fora_do_contrato(texto):
    with pytest.raises(ValidationError):
        decodificar_interpretacao(texto)
