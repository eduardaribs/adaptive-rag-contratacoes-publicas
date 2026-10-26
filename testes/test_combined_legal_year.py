import pytest
from src.router import planejar_consulta
from src.query_executor import executar_consulta


def analise(pergunta):
    return {
        "query": pergunta,
        "query_id": "q_ano_legal",
        "routes": ["estruturada", "normativa"],
        "filters": {"ano": 2026},
        "is_refusal": False,
    }


@pytest.mark.parametrize("referencia", [
    "Lei nº 14.133/2021",
    "Lei 14.133/2021",
    "Lei Complementar nº 123/2006",
    "Decreto nº 11.462/2023",
])
def test_ano_legal_nao_vira_intervalo_da_compra(referencia):
    pergunta = (
        "Quantas contratações têm ano da compra 2026 "
        f"e o que a {referencia} estabelece sobre o pregão?"
    )
    plano = planejar_consulta(pergunta, analise=analise(pergunta))

    assert plano["estrategia"] == "combinada"
    assert plano["filtros"] == {"ano_compra": 2026}


def test_intervalo_real_continua_exigindo_esclarecimento():
    pergunta = (
        "Quantas contratações têm ano da compra 2025 e 2026 "
        "e o que a Lei nº 14.133/2021 estabelece sobre o pregão?"
    )
    plano = planejar_consulta(pergunta, analise=analise(pergunta))
    assert plano["necessita_esclarecimento"] is True


def test_ano_legal_sozinho_nao_cria_filtro_de_compra():
    pergunta = (
        "Quantas contratações existem e o que a "
        "Lei nº 14.133/2021 estabelece sobre o pregão?"
    )
    plano = planejar_consulta(pergunta, analise=analise(pergunta))
    assert plano["estrategia"] == "combinada"
    assert "ano_compra" not in plano["filtros"]


def test_execucao_preserva_pergunta_e_separa_filtros():
    pergunta = (
        "Quantas contratações têm ano da compra 2026 "
        "e o que a Lei nº 14.133/2021 estabelece sobre o pregão?"
    )
    chamadas = []

    def recuperar(**kwargs):
        chamadas.append(kwargs)
        assert kwargs["pergunta"] == (
            "o que a Lei nº 14.133/2021 estabelece sobre o pregão?"
        )
        assert kwargs["analise_pronta"]["query"] == kwargs["pergunta"]
        assert kwargs["analise_pronta"]["filters"] == {}
        assert kwargs["analise_pronta"]["routes"] == ["normativa"]
        return {
            "query_id": "q_ano_legal",
            "routes": ["normativa"],
            "evidences": [],
        }

    resultado = executar_consulta(
        pergunta,
        base=[
            {"id_pncp": "1", "ano_compra": "2026",
             "fonte_original": "teste.json"},
            {"id_pncp": "2", "ano_compra": "2025",
             "fonte_original": "teste.json"},
        ],
        analise=analise(pergunta),
        recuperador=recuperar,
        run_id="run_ano_legal",
        client=object(),
    )

    assert resultado["executado"] is True
    assert resultado["estrategia"] == "combinada"
    assert resultado["total"] == 1
    assert resultado["query_id"] == "q_ano_legal"
    assert resultado["run_id"] == "run_ano_legal"
    assert len(chamadas) == 1

    assert resultado["query"] == pergunta
    assert resultado["hibrida"]["query_original"] == pergunta
