from copy import deepcopy

from app import pipeline_adapter
from app.interface_results import preparar_estruturado, preparar_combinado
from src.technology_classifier import VERSAO_CRITERIO


def resultado():
    return {
        "query": "Quantas contratações envolvem tecnologia?",
        "query_id": "q_tic_interface",
        "run_id": "run_tic_interface",
        "estrategia": "consulta_estruturada",
        "operacao": "contar",
        "total": 2,
        "total_base": 4,
        "fontes": ["teste.json"],
        "filtros_aplicados": {},
        "criterio_objeto": "Critério contextual documentado.",
        "criterio_tecnologia": {
            "implementacao": VERSAO_CRITERIO,
            "descricao": "Critério contextual documentado.",
            "tipo": "todos",
        },
        "resumo_tecnologia": {
            "tic_proposto": 2,
            "revisao": 1,
            "sem_indicio": 1,
            "classificacao_humana_validada": False,
        },
        "classificacoes_tecnologia": [
            {"id_pncp": "1", "status": "tic_proposto"}
        ],
    }


def test_estruturado_informa_criterio_e_classificacao_proposta():
    original = resultado()
    copia = deepcopy(original)
    saida = preparar_estruturado(original)

    assert original == copia
    assert "Critério contextual documentado." in saida["answer"]
    assert "proposta, sujeita a revisão" in saida["answer"]
    assert "Validação humana:** não confirmada" in saida["answer"]
    assert saida["total"] == 2


def test_combinado_preserva_campos_tic_sem_mutacao():
    estruturada = resultado()
    original = deepcopy(estruturada)

    saida = preparar_combinado(
        {
            "estruturada": estruturada,
            "plano": {"estrategia": "combinada"},
            "routes": ["estruturada", "normativa"],
        },
        {
            "answer": "Trecho documental.",
            "fontes": ["lei.html"],
            "query_id": "q_tic_interface",
            "run_id": "run_tic_interface",
        },
    )

    assert estruturada == original
    for campo in (
        "criterio_tecnologia",
        "resumo_tecnologia",
        "classificacoes_tecnologia",
    ):
        assert saida[campo] == original[campo]
    assert "proposta, sujeita a revisão" in saida["answer"]
    assert saida["total"] == 2


def test_adaptador_fornece_criterio_contextual(monkeypatch):
    chamadas = []

    def executar(**kwargs):
        chamadas.append(kwargs)
        return resultado()

    monkeypatch.setattr(pipeline_adapter, "executar_consulta", executar)

    saida = pipeline_adapter.executar_pipeline(
        "Quantas contratações envolvem tecnologia?"
    )

    criterio = chamadas[0]["criterio_tecnologia"]
    assert criterio["implementacao"] == VERSAO_CRITERIO
    assert "evidência textual suficiente" in criterio["regra_principal"]
    assert saida["total"] == 2
