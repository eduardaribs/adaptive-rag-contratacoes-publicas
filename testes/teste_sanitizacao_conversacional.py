"""Testes de recuperação segura da base conversacional."""

from src.retrieve import (
    _sanitizar_texto_evidencia,
    chunk_atende_filtros,
)


def criar_chunk_conversacional(texto):
    return {
        "chunk_id": "ata_teste_chunk_1",
        "text": texto,
        "metadata": {
            "chunk_id": "ata_teste_chunk_1",
            "natureza": "conversacional",
            "base_id": "base_conversacional",
            "sensitivity": "restrito",
            "uf": "RJ",
        },
    }


def test_restrito_conversacional_pode_seguir_para_sanitizacao():
    chunk = criar_chunk_conversacional("Conteúdo da ata.")

    assert chunk_atende_filtros(chunk, {}) is True


def test_restrito_de_outra_natureza_permanece_bloqueado():
    chunk = criar_chunk_conversacional("Conteúdo restrito.")
    chunk["metadata"]["natureza"] = "estruturada"

    assert chunk_atende_filtros(chunk, {}) is False


def test_sanitiza_email_telefone_e_cpf():
    texto = (
        "Contato: pessoa@email.com, "
        "telefone (21) 98765-4321 e "
        "CPF 123.456.789-10."
    )

    seguro, sensitivity = _sanitizar_texto_evidencia(
        texto,
        "restrito",
    )

    assert "pessoa@email.com" not in seguro
    assert "98765-4321" not in seguro
    assert "123.456.789-10" not in seguro
    assert "[EMAIL_OCULTO]" in seguro
    assert "[TELEFONE_OCULTO]" in seguro
    assert "[CPF_OCULTO]" in seguro
    assert sensitivity == "restrito_sanitizado"


def test_texto_publico_e_preservado():
    texto = "Informação pública sobre contratação."

    seguro, sensitivity = _sanitizar_texto_evidencia(
        texto,
        "publico",
    )

    assert seguro == texto
    assert sensitivity == "publico"
