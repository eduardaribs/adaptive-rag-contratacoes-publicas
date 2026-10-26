
import json
from types import SimpleNamespace
from src.grounded_quotes import preparar_selecao_extrativa

def evidencia():
    return SimpleNamespace(
        chunk_id="def", natureza="normativa",
        text=("Art. 6º Definições: XL - leilão: maior lance; "
              "XLI - pregão: bens e serviços comuns; "
              "XLII - diálogo competitivo: diálogos com licitantes;"),
    )

def test_recorta_definicao_literal_sem_outras_definicoes():
    e = evidencia()
    texto, fontes = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["def"]}), [e],
        pergunta="O que a lei estabelece sobre o pregão?",
    )
    assert "XLI - pregão: bens e serviços comuns;" in texto
    assert "leilão" not in texto
    assert "diálogo competitivo" not in texto
    assert fontes == [e]
    assert "leilão" in e.text

def test_pedido_do_artigo_completo_preserva_original():
    e = evidencia()
    texto, _ = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["def"]}), [e],
        pergunta="O que o artigo 6 estabelece sobre pregão?",
    )
    assert e.text in texto

def test_artigo_29_preserva_excecoes():
    e = SimpleNamespace(
        chunk_id="regra", natureza="normativa",
        text="Art. 29. Regra de aplicação. Parágrafo único. Exceções.",
    )
    texto, _ = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["regra"]}), [e],
        pergunta="O que a lei estabelece sobre o pregão?",
    )
    assert e.text in texto
