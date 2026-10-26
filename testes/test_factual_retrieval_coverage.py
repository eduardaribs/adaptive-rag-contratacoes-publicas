import copy

import pytest

from src.factual_selection import cobrir_campos_ata
from src.retrieve import selecionar_resultados_multirrota


def dados():
    textos = [
        ("generico", "Condições gerais.", "conversacional"),
        ("fabricante", "Fabricante e marca: FABRICA EXEMPLO.", "conversacional"),
        ("prazo", "Prazo de validade.", "conversacional"),
        ("objeto", "A presente ata tem por objeto a aquisição de peças.", "conversacional"),
        ("contratada", "EMPRESA EXEMPLO, doravante denominada CONTRATADA.", "conversacional"),
        ("pncp", '{"numeroControlePNCP": "12345678000190-1-000001/2026"}', "estruturada"),
    ]
    corpus = {
        identificador: {
            "text": texto,
            "metadata": {
                "chunk_id": identificador,
                "natureza": natureza,
            },
        }
        for identificador, texto, natureza in textos
    }
    ranking = [
        {"chunk_id": identificador, "rrf_score": 1 / (i + 1)}
        for i, (identificador, _, _) in enumerate(textos)
    ]
    return ranking, corpus


@pytest.mark.parametrize("pergunta, campos", [
    (
        "Informe o objeto da ata nº 191/2026 e o número PNCP.",
        {"objeto", "pncp"},
    ),
    (
        "Na ata nº 137/2026, qual é o objeto e qual empresa é a contratada?",
        {"objeto", "contratada"},
    ),
])
def test_preserva_campos_apos_selecao_multirrota(pergunta, campos):
    ranking, corpus = dados()
    original = copy.deepcopy(ranking)
    rotas = ["conversacional", "estruturada"]
    ajustado = cobrir_campos_ata(
        pergunta, ranking, corpus, rotas, 3, set(corpus)
    )
    finais = selecionar_resultados_multirrota(
        ajustado, corpus, rotas, 3
    )
    assert campos <= {item["chunk_id"] for item in finais}
    assert ranking == original
    assert {i["chunk_id"]: i["rrf_score"] for i in ajustado} == {
        i["chunk_id"]: i["rrf_score"] for i in original
    }


def test_sem_escopo_nao_promove():
    ranking, corpus = dados()
    assert cobrir_campos_ata(
        "Qual o objeto da ata?", ranking, corpus,
        ["conversacional"], 3, None,
    ) == ranking


def test_nao_promove_candidato_fora_do_escopo():
    ranking, corpus = dados()
    ajustado = cobrir_campos_ata(
        "Qual o objeto da ata?", ranking, corpus,
        ["conversacional"], 3, set(corpus) - {"objeto"},
    )
    assert "objeto" not in {i["chunk_id"] for i in ajustado[:3]}


def test_limite_insuficiente_preserva_ranking():
    ranking, corpus = dados()
    assert cobrir_campos_ata(
        "Qual o objeto da ata e o número PNCP?", ranking, corpus,
        ["conversacional", "estruturada"], 1, set(corpus),
    ) == ranking


def test_campos_ja_no_top3_resistem_a_reserva_de_outra_rota():
    ranking, corpus = dados()
    por_id = {item["chunk_id"]: item for item in ranking}
    ranking = [
        por_id[nome] for nome in (
            "generico", "objeto", "contratada",
            "fabricante", "prazo", "pncp",
        )
    ]
    rotas = ["conversacional", "estruturada"]
    ajustado = cobrir_campos_ata(
        "Na ata nº 137/2026, qual é o objeto e qual empresa é a contratada?",
        ranking, corpus, rotas, 3, set(corpus),
    )
    finais = selecionar_resultados_multirrota(
        ajustado, corpus, rotas, 3
    )
    assert {item["chunk_id"] for item in finais} == {
        "objeto", "contratada", "pncp",
    }
