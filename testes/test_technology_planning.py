from src.router import planejar_consulta
from src.query_executor import executar_consulta


def analise():
    return {
        "query_id": "q_tic",
        "routes": ["estruturada"],
        "filters": {},
        "is_refusal": False,
    }


def test_criterio_contextual_nao_vira_contagem_por_palavras():
    resultado = executar_consulta(
        "Quantas contratações envolvem tecnologia?",
        base=[],
        analise=analise(),
        criterio_tecnologia={
            "status": "definido",
            "regra_principal": "Exige evidência contextual de TIC.",
            "termos_indicativos": ["software", "rede"],
            # Mesmo com campos antigos, não pode virar filtro textual.
            "termos": ["software", "rede"],
            "descricao": "Critério contextual.",
        },
    )

    assert resultado["executado"] is False
    assert resultado["plano"]["necessita_esclarecimento"] is True
    assert "total validado" in resultado["mensagem"]
    assert "total" not in resultado


def test_criterio_textual_explicito_continua_disponivel():
    resultado = executar_consulta(
        "Quantas contratações envolvem tecnologia?",
        base=[
            {
                "id_pncp": "1",
                "objeto": "Aquisição de software.",
                "fonte_original": "teste.json",
            },
            {
                "id_pncp": "2",
                "objeto": "Aquisição de mobiliário.",
                "fonte_original": "teste.json",
            },
        ],
        analise=analise(),
        criterio_tecnologia={
            "termos": ["software"],
            "descricao": (
                "Critério textual: objeto contém software. "
                "Não representa classificação contextual de TIC."
            ),
        },
    )

    assert resultado["executado"] is True
    assert resultado["total"] == 1
    assert resultado["criterio_objeto"].startswith("Critério textual:")


def test_quais_contratacoes_planeja_listagem():
    plano = planejar_consulta(
        "Quais contratações envolvem tecnologia?",
        analise=analise(),
        criterio_tecnologia={
            "termos": ["software"],
            "descricao": "Critério textual: objeto contém software.",
        },
    )

    assert plano["operacao"] == "listar"


def test_pergunta_aberta_preserva_busca_hibrida():
    plano = planejar_consulta(
        "Existe contratação para reparo de vidraça?",
        analise=analise(),
    )

    assert plano["estrategia"] == "recuperacao_hibrida"
    assert plano["operacao"] == "buscar"
