import sys
import os

# Adiciona a pasta src ao caminho para conseguir importar o ingest.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from ingest import extrair_ano

def test_extracao_ano_offline():
    # Testes mínimos exigidos pelo planeamento
    assert extrair_ano("01/01/2026") == "2026"
    assert extrair_ano("01/12/2026") == "2026"
    assert extrair_ano("09/07/2026") == "2026"
    assert extrair_ano("2026-09-18") == "2026"

    # Testes de segurança adicionais
    assert extrair_ano("2026") == "2026"
    assert extrair_ano("01/0") == ""
    assert extrair_ano("texto sem data") == ""

    print("✅ TESTE OFFLINE APROVADO: A extração de ano ignorou formatos inválidos e extraiu os corretos!")

if __name__ == "__main__":
    test_extracao_ano_offline()
