import pytest

from src.context_budget import limitar_contexto_normativo
from src.schema import SourceEvidence


def evidencia(identificador, texto, natureza="normativa"):
    return SourceEvidence(
        chunk_id=identificador,
        text=texto,
        natureza=natureza,
    )


def montar(evidencias):
    return "\n".join(e.text for e in evidencias)


def test_prioriza_assunto_solicitado_sem_id_fixo():
    entradas = [
        evidencia("outro", "Padronização. " * 60),
        evidencia("relevante", "Pregão: condições e exceções."),
    ]
    selecionadas, detalhes = limitar_contexto_normativo(
        entradas, "Explique o pregão e suas exceções.", montar, limite=500
    )
    assert [e.chunk_id for e in selecionadas] == ["relevante"]
    assert detalhes[0]["incluida_no_contexto"] is False
    assert detalhes[0]["caracteres_enviados"] == 0


def test_nao_corta_condicao_no_meio():
    texto = "Pregão permitido sob condição. " + "Condição integral. " * 40
    with pytest.raises(ValueError, match="cabe inteira"):
        limitar_contexto_normativo(
            [evidencia("grande", texto)], "Pregão", montar, limite=500
        )


def test_nao_modifica_evidencias_originais():
    original = evidencia("a", "Pregão e condições.")
    selecionadas, _ = limitar_contexto_normativo(
        [original], "Pregão", montar, limite=500
    )
    assert selecionadas[0].text == original.text
    assert original.text == "Pregão e condições."


def test_respeita_tamanho_total_incluindo_montagem():
    entradas = [
        evidencia("a", "Pregão. " * 30),
        evidencia("b", "Pregão. " * 30),
    ]
    selecionadas, _ = limitar_contexto_normativo(
        entradas, "Pregão", montar, limite=500
    )
    assert len(montar(selecionadas)) <= 500
    assert len(selecionadas) == 2


def test_nao_aplica_limite_a_resultado_calculado_ou_ata():
    entradas = [evidencia("calculo", "x" * 3000, "agregada")]
    selecionadas, detalhes = limitar_contexto_normativo(
        entradas, "Explique", montar, limite=500
    )
    assert selecionadas == entradas
    assert detalhes == []
