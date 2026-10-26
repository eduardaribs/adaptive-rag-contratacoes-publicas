import json
import os

def test_metadados_obrigatorios():
    caminho = "data/processed/chunks_teste.json"
    if not os.path.exists(caminho):
        print("⚠️ Arquivo de chunks não encontrado.")
        return

    with open(caminho, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    chaves_obrigatorias = ["source_file", "doc_type", "chunk_id", "sensitivity", "base_id"]
    erros = 0

    print("Iniciando varredura offline de metadados...")
    for idx, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        for chave in chaves_obrigatorias:
            if chave not in meta:
                print(f"❌ Falha no chunk {idx}: Metadado '{chave}' ausente.")
                erros += 1

    if erros == 0:
        print(f"✅ TESTE OFFLINE PASSOU: Todos os {len(chunks)} chunks contêm os metadados obrigatórios do checklist!")
    else:
        print(f"⚠️ Falhou com {erros} erros.")

if __name__ == "__main__":
    test_metadados_obrigatorios()
