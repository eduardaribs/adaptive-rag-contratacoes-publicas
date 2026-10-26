from copy import deepcopy

import pytest

from src.retrieval_method_coverage import cobrir_metodos
from src.context_budget import limitar_contexto_normativo
from src.schema import SourceEvidence


def item(identificador, score=1.0):
    return {"chunk_id": identificador, "rrf_score": score}


def test_preserva_dois_lexicais_e_um_denso_sem_mudar_scores():
    ranking = [item("comum"), item("denso"), item("lexico_a"), item("lexico_b")]
    antes = deepcopy(ranking)
    resultado = cobrir_metodos(
        ranking,
        [item("denso"), item("comum")],
        [item("lexico_a"), item("lexico_b")],
        3,
    )
    assert {i["chunk_id"] for i in resultado[:3]} == {
        "denso", "lexico_a", "lexico_b",
    }
    assert sorted(resultado, key=lambda i: i["chunk_id"]) == sorted(
        antes, key=lambda i: i["chunk_id"]
    )
    assert ranking == antes


@pytest.mark.parametrize("top_k", [0, 1])
def test_sem_espaco_para_diversidade_preserva_ranking(top_k):
    ranking = [item("a"), item("b")]
    assert cobrir_metodos(
        ranking, [item("b")], [item("a")], top_k
    ) == ranking


def test_nao_acrescenta_ids_fora_dos_candidatos_elegiveis():
    ranking = [item("a"), item("b"), item("c")]
    resultado = cobrir_metodos(
        ranking,
        [item("externo"), item("c")],
        [item("a"), item("b")],
        3,
    )
    assert {i["chunk_id"] for i in resultado} == {"a", "b", "c"}


def test_sobreposicao_entre_metodos_nao_duplica_resultados():
    ranking = [item("a"), item("b"), item("c")]
    resultado = cobrir_metodos(
        ranking,
        [item("a"), item("c")],
        [item("a"), item("b")],
        3,
    )
    assert len({i["chunk_id"] for i in resultado}) == 3


def test_sem_resultados_lexicais_preserva_ranking():
    ranking = [item("a"), item("b")]
    assert cobrir_metodos(ranking, [item("b")], [], 2) == ranking


def test_orcamento_padrao_comporta_trechos_complementares(monkeypatch):
    monkeypatch.delenv("NORMATIVE_CONTEXT_MAX_CHARS", raising=False)
    evidencias = [
        SourceEvidence(
            chunk_id="a", source_file="lei.html",
            natureza="normativa", text="Etapa. " + "a" * 1800,
        ),
        SourceEvidence(
            chunk_id="b", source_file="lei.html",
            natureza="normativa", text="Autoridade. " + "b" * 1800,
        ),
    ]

    def montar(itens):
        return "\n".join(e.text for e in itens)

    selecionadas, detalhes = limitar_contexto_normativo(
        evidencias, "Explique a etapa e a autoridade.", montar
    )
    assert {e.chunk_id for e in selecionadas} == {"a", "b"}
    assert all(d["limite_contexto_caracteres"] == 6000 for d in detalhes)
