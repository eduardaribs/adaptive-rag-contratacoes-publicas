import json
from types import SimpleNamespace

import pytest

from src import analytical_interpreter as interpretador
from src.query_decomposition import separar_pedidos, extrair_pedido_documental


@pytest.mark.parametrize("conector", [
    " e ",
    "; ",
    ". Depois ",
    ". Em seguida, ",
])
def test_separa_sem_perder_filtro_analitico(conector):
    prefixo = "Conte os itens homologados do PE 038/26/2026"
    documental = "explique quando a Lei 14.133 exige o pregão."
    pergunta = prefixo + conector + documental
    partes = separar_pedidos(pergunta)
    assert partes["analitica"] == prefixo
    assert partes["documental"] == documental
    assert extrair_pedido_documental(pergunta) == documental


def test_instrucao_de_brevidade_nao_vira_documental():
    pergunta = (
        "No PE 038/26/2026, quantos itens foram homologados? "
        "Responda em uma frase."
    )
    assert separar_pedidos(pergunta) == {
        "analitica": pergunta, "documental": None
    }


def test_campos_de_listagem_nao_viram_documental():
    pergunta = "Liste os itens e informe fornecedor e valor."
    assert extrair_pedido_documental(pergunta) is None


def test_pedido_extraido_sobrevive_ao_null_do_modelo(monkeypatch, tmp_path):
    monkeypatch.setattr(interpretador.obs, "PASTA_LOGS", tmp_path)
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
                        "formato": "automatico",
                        "pendencias": [],
                    },
                })),
            )],
            usage=None,
        )

    cliente = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=criar)
        )
    )
    pergunta = (
        "Conte os itens homologados do PE 038/26/2026. "
        "Depois explique quando a Lei 14.133 exige o pregão."
    )
    resultado = interpretador.interpretar_analitica(
        pergunta, client=cliente
    )

    assert resultado["pedido_documental"] == (
        "explique quando a Lei 14.133 exige o pregão."
    )
    assert resultado["pergunta_analitica"] == (
        "Conte os itens homologados do PE 038/26/2026"
    )
    mensagem_usuario = chamadas[0]["messages"][1]["content"]
    assert "Conte os itens homologados" in mensagem_usuario
    assert "explique quando" not in mensagem_usuario
    assert "Lei 14.133 exige" not in mensagem_usuario
