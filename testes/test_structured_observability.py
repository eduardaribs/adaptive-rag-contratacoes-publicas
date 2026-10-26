import json
import pytest

from src import obs
from src.query_executor import executar_consulta


@pytest.fixture
def eventos(monkeypatch):
    capturados = []

    def registrar(**kwargs):
        capturados.append(kwargs)

    monkeypatch.setattr(obs, "registrar_evento", registrar)
    return capturados


def base_teste():
    return [{
        "id_pncp": "1",
        "ano_compra": "2026",
        "objeto": "TEXTO_DO_REGISTRO_NAO_DEVE_IR_PARA_O_LOG",
        "fonte_original": "teste.json",
    }]


def analise_teste():
    return {
        "query_id": "q_obs_teste",
        "routes": ["estruturada"],
        "filters": {"ano": 2026},
        "is_refusal": False,
    }


def test_evento_contagem_com_ids_e_totais(eventos):
    resultado = executar_consulta(
        "Quantas contratações têm ano da compra 2026?",
        base=base_teste(),
        analise=analise_teste(),
        run_id="run_obs_teste",
    )

    assert len(eventos) == 1
    evento = eventos[0]

    assert evento["stage"] == "consulta_estruturada"
    assert evento["status"] == "ok"
    assert evento["run_id"] == resultado["run_id"] == "run_obs_teste"
    assert evento["query_id"] == resultado["query_id"] == "q_obs_teste"
    assert evento["latencia_ms"] >= 0
    assert evento["output_data"]["total"] == 1
    assert evento["output_data"]["quantidade_retornada"] == 0


def test_log_listagem_nao_contem_texto_dos_registros(eventos):
    executar_consulta(
        "Liste as contratações de 2026; mostre apenas objeto.",
        base=base_teste(),
        analise=analise_teste(),
    )

    evento = eventos[0]

    assert evento["output_data"]["quantidade_retornada"] == 1
    assert evento["output_data"]["campos"] == ["objeto"]

    serializado = json.dumps(evento, ensure_ascii=False)
    assert "TEXTO_DO_REGISTRO_NAO_DEVE_IR_PARA_O_LOG" not in serializado
    assert "registros" not in evento["output_data"]


def test_falha_da_consulta_e_registrada_e_propagada(eventos, monkeypatch):
    import src.query_executor as executor

    def falhar(*args, **kwargs):
        raise RuntimeError("Falha controlada de teste.")

    monkeypatch.setattr(executor, "consultar_registros", falhar)

    with pytest.raises(RuntimeError, match="Falha controlada"):
        executar_consulta(
            "Quantas contratações têm ano da compra 2026?",
            base=base_teste(),
            analise=analise_teste(),
            run_id="run_erro_teste",
        )

    assert len(eventos) == 1
    evento = eventos[0]

    assert evento["stage"] == "consulta_estruturada"
    assert evento["status"] == "erro"
    assert evento["run_id"] == "run_erro_teste"
    assert evento["query_id"] == "q_obs_teste"
    assert evento["output_data"]["erro"] == "RuntimeError"
