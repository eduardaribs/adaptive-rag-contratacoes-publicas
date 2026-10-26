import pytest
from src.index import gerar_chave_cache

def test_determinismo_do_cache():
    """Garante que o mesmo ID, texto e modelo geram exatamente a mesma chave (Hash)."""
    chave1 = gerar_chave_cache("chunk_1", "Texto de teste para a licitação", "qwen3")
    chave2 = gerar_chave_cache("chunk_1", "Texto de teste para a licitação", "qwen3")
    assert chave1 == chave2

def test_sensibilidade_a_mudancas_no_texto():
    """Garante que se o conteúdo do documento mudar, o cache é invalidado gerando nova chave."""
    chave_original = gerar_chave_cache("chunk_2", "O valor do contrato é 100", "qwen3")
    chave_alterada = gerar_chave_cache("chunk_2", "O valor do contrato é 200", "qwen3")
    assert chave_original != chave_alterada

def test_sensibilidade_a_mudanca_de_modelo():
    """Garante que a troca do modelo de embeddings obriga a gerar novos vetores."""
    chave_modelo_a = gerar_chave_cache("chunk_3", "Mesmo texto", "qwen3")
    chave_modelo_b = gerar_chave_cache("chunk_3", "Mesmo texto", "text-embedding-3-small")
    assert chave_modelo_a != chave_modelo_b
