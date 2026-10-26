
import json
from types import SimpleNamespace
from src.grounded_quotes import preparar_selecao_extrativa

PERGUNTA = "Qual é o objeto da ata e o número de controle PNCP associado?"

def test_objeto_e_pncp_literais_preservam_fontes_e_originais():
    ata = SimpleNamespace(
        chunk_id="ata",
        text=("Representação e condições. A presente ata tem por objeto "
              "a aquisição de peças para o hospital, conforme especificado "
              "no Termo de Referência."),
    )
    registro = SimpleNamespace(
        chunk_id="registro",
        text=json.dumps({
            "numeroControlePNCP": "123-1-456/2026",
            "outroCampo": "informação desnecessária",
        }),
    )
    original = (ata.text, registro.text)
    resposta, fontes = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["ata", "registro"]}),
        [ata, registro], pergunta=PERGUNTA,
    )
    assert "aquisição de peças para o hospital" in resposta
    assert "123-1-456/2026" in resposta
    assert "outroCampo" not in resposta
    assert "Representação" not in resposta
    assert "[Fonte: ata]" in resposta
    assert "[Fonte: registro]" in resposta
    assert fontes == [ata, registro]
    assert (ata.text, registro.text) == original

def test_pergunta_sobre_condicoes_preserva_texto():
    e = SimpleNamespace(
        chunk_id="ata",
        text="A ata tem por objeto peças, conforme especificado no anexo.",
    )
    resposta, _ = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["ata"]}), [e],
        pergunta="Quais são as condições da ata?",
    )
    assert e.text in resposta

def test_limite_desconhecido_preserva_texto():
    e = SimpleNamespace(
        chunk_id="ata", text="Descrição sem delimitação reconhecida.",
    )
    resposta, _ = preparar_selecao_extrativa(
        json.dumps({"chunk_ids": ["ata"]}), [e], pergunta=PERGUNTA,
    )
    assert e.text in resposta
