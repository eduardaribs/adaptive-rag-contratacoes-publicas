import pytest
from src.ingest import fatiar_texto


def test_preserva_inicio_meio_e_final_de_texto_longo():
    palavras = [f"palavra{i:04d}" for i in range(1000)]
    texto = " ".join(palavras)
    blocos = fatiar_texto(texto, max_chars=200, overlap=40)

    assert len(blocos) > 1
    assert blocos[0].startswith(palavras[0])
    assert blocos[-1].endswith(palavras[-1])
    assert all(len(bloco) <= 200 for bloco in blocos)
    assert all(any(palavra in bloco for bloco in blocos)
               for palavra in palavras)


def test_texto_sem_espacos_nao_perde_final():
    texto = "A" * 450 + "FINAL"
    blocos = fatiar_texto(texto, max_chars=100, overlap=20)

    reconstruido = blocos[0] + "".join(
        bloco[20:] for bloco in blocos[1:]
    )
    assert reconstruido == texto


def test_preserva_cauda_curta():
    texto = "A" * 100 + "FIM"
    assert fatiar_texto(texto, max_chars=100, overlap=0) == [
        "A" * 100, "FIM"
    ]


def test_texto_curto_e_vazio():
    assert fatiar_texto("Texto curto.") == ["Texto curto."]
    assert fatiar_texto("") == []
    assert fatiar_texto("   ") == []


@pytest.mark.parametrize("max_chars,overlap", [
    (0, 0), (-1, 0), (100, -1), (100, 100), (100, 101),
])
def test_rejeita_parametros_sem_avanco_valido(max_chars, overlap):
    with pytest.raises(ValueError):
        fatiar_texto("texto", max_chars=max_chars, overlap=overlap)
