import pytest

from src import obs
from src.query_executor import executar_plano


def plano():
    return {
        "bases": ["agregada"],
        "estrategia": "consulta_agregada",
        "operacao": "resumir_pca",
        "filtros": {},
        "query_id": "q_obs_agregada",
    }


def test_agregada_registra_sucesso_com_ids_e_totais(monkeypatch):
    import src.aggregate_query as aggregate

    eventos = []
    monkeypatch.setattr(
        obs, "registrar_evento",
        lambda **kwargs: eventos.append(kwargs),
    )
    monkeypatch.setattr(
        aggregate, "executar_agregada",
        lambda plano: {
            "estrategia": "consulta_agregada",
            "operacao": "resumir_pca",
            "total_itens": 2,
            "valor_total_estimado": "10.0001",
            "itens_sem_valor": 0,
            "soma_completa": True,
            "fontes": ["pca.csv"],
        },
    )

    resultado = executar_plano(
        "Resumo do PCA.",
        plano(),
        run_id="run_obs_agregada",
    )

    assert "consulta_agregada" in obs.STAGES_VALIDOS
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento["stage"] == "consulta_agregada"
    assert evento["status"] == "ok"
    assert evento["query_id"] == resultado["query_id"] == "q_obs_agregada"
    assert evento["run_id"] == resultado["run_id"] == "run_obs_agregada"
    assert evento["output_data"]["total_itens"] == 2
    assert evento["output_data"]["valor_total_estimado"] == "10.0001"
    assert evento["latencia_ms"] >= 0


def test_agregada_registra_erro_sem_ocultar_falha(monkeypatch):
    import src.aggregate_query as aggregate

    eventos = []
    monkeypatch.setattr(
        obs, "registrar_evento",
        lambda **kwargs: eventos.append(kwargs),
    )

    def falhar(plano):
        raise ValueError("Valor inválido no CSV.")

    monkeypatch.setattr(aggregate, "executar_agregada", falhar)

    with pytest.raises(ValueError, match="Valor inválido"):
        executar_plano(
            "Resumo do PCA.",
            plano(),
            run_id="run_erro_agregada",
        )

    assert len(eventos) == 1
    evento = eventos[0]
    assert evento["stage"] == "consulta_agregada"
    assert evento["status"] == "erro"
    assert evento["query_id"] == "q_obs_agregada"
    assert evento["run_id"] == "run_erro_agregada"
    assert evento["output_data"]["erro"] == "ValueError"


def test_agregada_sem_query_id_reutiliza_identificador_do_log(monkeypatch):
    import src.aggregate_query as aggregate

    eventos = []

    monkeypatch.setattr(
        obs, "registrar_evento",
        lambda **kwargs: eventos.append(kwargs),
    )
    monkeypatch.setattr(
        aggregate, "executar_agregada",
        lambda plano: {
            "operacao": "resumir_pca",
            "total_itens": 2,
        },
    )

    plano_sem_id = {
        "bases": ["agregada"],
        "estrategia": "consulta_agregada",
        "operacao": "resumir_pca",
        "filtros": {},
    }

    resultado = executar_plano("Resumo do PCA.", plano_sem_id)

    assert len(eventos) == 1
    assert resultado["query_id"]
    assert resultado["run_id"]
    assert resultado["query_id"] == eventos[0]["query_id"]
    assert resultado["run_id"] == eventos[0]["run_id"]
