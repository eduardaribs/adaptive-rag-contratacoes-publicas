import json
from types import SimpleNamespace

from src.analytical_transport import decodificar_interpretacao


def test_ausencia_de_pedido_documental_equivale_a_null():
    entrada = {
        "tipo": "esclarecimento",
        "mensagem": "A pergunta exige uma explicação documental.",
        "plano": None,
    }
    resultado = decodificar_interpretacao(json.dumps(entrada))
    assert resultado["tipo"] == "esclarecimento"
    assert resultado["plano"] is None
    assert resultado["pedido_documental"] is None


def test_campo_opcional_ausente_nao_provoca_reinterpretacao(
    monkeypatch, tmp_path
):
    from src import analytical_interpreter as modulo
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    chamadas = []

    def criar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=json.dumps({
                    "tipo": "esclarecimento",
                    "mensagem": "A pergunta exige explicação documental.",
                    "plano": None,
                })),
            )],
            usage=None,
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=criar)
        )
    )
    resultado = modulo.interpretar_analitica(
        "Explique o que significa homologação no PE 038/26/2026.",
        client=client,
        run_id="run_opcional",
        query_id="q_opcional",
    )
    assert len(chamadas) == 1
    assert resultado["tentativas"] == 1
    assert resultado["tipo"] == "esclarecimento"
    assert resultado["plano"] is None
    assert resultado["pedido_documental"] is None
