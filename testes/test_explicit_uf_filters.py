
import pytest
from src import router

UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()


@pytest.mark.parametrize("uf", UFS)
def test_sigla_em_localizacao_e_uf_nao_municipio(uf):
    pergunta = (
        f"Quantas contratações de pregão eletrônico foram "
        f"publicadas no {uf} em março de 2026?"
    )
    filtros = router._validar_filtros_contra_pergunta(
        pergunta, {"municipio": uf}
    )
    plano = router.planejar_consulta(
        pergunta,
        analise={
            "query_id": "q_uf",
            "routes": ["estruturada"],
            "filters": filtros,
            "is_refusal": False,
        },
    )
    assert plano["estrategia"] == "consulta_estruturada"
    assert plano["filtros"]["uf"] == uf
    assert not plano["filtros"].get("municipio")
    assert plano["filtros"]["data_inicial"] == "2026-03-01"


def test_uf_explicita_preserva_municipio_distinto():
    filtros = router._validar_filtros_contra_pergunta(
        "Liste contratações do município de Niterói no RJ.",
        {"municipio": "Niterói"},
    )
    assert filtros["uf"] == "RJ"
    assert filtros["municipio"] == "Niterói"


def test_sigla_dentro_de_processo_ficticio_nao_vira_uf():
    assert router._extrair_uf_explicita(
        "Qual prazo do processo fictício SIM-RJ-001?"
    ) is None


def test_varias_ufs_exigem_esclarecimento():
    plano = router.planejar_consulta(
        "Quantas contratações foram publicadas no AC e no RJ em março de 2026?",
        analise={
            "query_id": "q_multiplas_ufs",
            "routes": ["estruturada"],
            "filters": {},
            "is_refusal": False,
        },
    )
    assert plano["estrategia"] == "esclarecimento"
    assert plano["necessita_esclarecimento"] is True
