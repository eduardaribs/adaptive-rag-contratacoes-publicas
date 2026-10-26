import os
import json
import csv
import re
from bs4 import BeautifulSoup
import pypdf

inconsistencias_report = {
    "sem_valor": 0, "sem_ano_compra": 0, "sem_data_publicacao": 0, "sem_id_pncp": 0
}

def criar_chunk_base(texto, source_file, doc_type, chunk_idx, base_id, sensitivity, extras):
    metadata = {
        "chunk_id": f"{source_file}_chunk_{chunk_idx}",
        "source_file": source_file,
        "doc_type": doc_type,
        "sensitivity": sensitivity,
        "base_id": base_id
    }
    metadata.update(extras)
    return {"text": texto, "metadata": metadata}

def extrair_ano(data_str):
    if not data_str: return ""
    data_str = str(data_str).strip()
    match_iso = re.search(r'^(\d{4})-\d{2}-\d{2}', data_str)
    if match_iso: return match_iso.group(1)
    match_br = re.search(r'\d{2}/\d{2}/(\d{4})', data_str)
    if match_br: return match_br.group(1)
    match_year = re.search(r'^(\d{4})$', data_str)
    if match_year: return match_year.group(1)
    return ""

def extrair_metadados_especificos(natureza, dados=None):
    global inconsistencias_report
    meta = {
        "natureza": natureza, "uf": "", "ano": "", "modalidade": "",
        "orgao": "", "municipio": "", "valor": "", "fornecedor": "", "vigencia": ""
    }
    if dados is None: return meta

    if natureza == "estruturada":
        unidade_orgao = dados.get("unidadeOrgao", {}) or {}
        orgao_entidade = dados.get("orgaoEntidade", {}) or {}

        id_pncp = dados.get("numeroControlePNCP") or dados.get("id")
        if not id_pncp: inconsistencias_report["sem_id_pncp"] += 1

        meta["id_pncp"] = id_pncp
        meta["uf"] = unidade_orgao.get("ufSigla", "")
        meta["municipio"] = unidade_orgao.get("municipioNome", "")
        meta["orgao"] = orgao_entidade.get("razaoSocial", "")
        meta["objeto"] = dados.get("objetoCompra", "")
        meta["modalidade"] = dados.get("modalidadeNome", "")

        ano_compra = dados.get("anoCompra")
        if not ano_compra: inconsistencias_report["sem_ano_compra"] += 1
        meta["ano_compra"] = str(ano_compra) if ano_compra else ""
        meta["ano"] = meta["ano_compra"]

        data_publicacao = dados.get("dataPublicacaoPncp")
        data_atualizacao = dados.get("dataAtualizacao")
        if not data_publicacao: inconsistencias_report["sem_data_publicacao"] += 1

        meta["data_publicacao"] = str(data_publicacao) if data_publicacao else ""
        meta["data_atualizacao"] = str(data_atualizacao) if data_atualizacao else ""

        valor_homologado = dados.get("valorTotalHomologado")
        valor_estimado = dados.get("valorTotalEstimado")

        if valor_homologado is not None:
            meta["valor_homologado"] = valor_homologado
            meta["valor"] = valor_homologado
        else:
            meta["valor_homologado"] = None

        if valor_estimado is not None:
            meta["valor_estimado"] = valor_estimado
            if valor_homologado is None:
                meta["valor"] = valor_estimado
        else:
            meta["valor_estimado"] = None

        if valor_homologado is None and valor_estimado is None:
            inconsistencias_report["sem_valor"] += 1
            meta["valor"] = ""

    elif natureza == "agregada":
        meta["orgao"] = dados.get("Órgão", dados.get("Unidade Responsável", dados.get("orgao", "")))
        vigencia = dados.get("Data Desejada", dados.get("data_homologacao", ""))
        meta["vigencia"] = vigencia
        ano_bruto = str(dados.get("Ano", dados.get("ano", "")))
        ano_val = extrair_ano(ano_bruto)
        if not ano_val and vigencia:
            ano_val = extrair_ano(vigencia)
        if not ano_val:
            for v in dados.values():
                if isinstance(v, str) and "/202" in v:
                    partes = v.split("/")
                    if len(partes) > 1:
                        ano_candidato = extrair_ano(partes[-1][:4])
                        if ano_candidato:
                            ano_val = ano_candidato
                            break
        meta["ano"] = ano_val
        meta["uf"] = dados.get("UF", dados.get("uf", "RJ"))
        meta["valor"] = dados.get("Valor Estimado", dados.get("Valor Total Estimado (R$)", dados.get("valor_total_homologado", "")))
        meta["fornecedor"] = dados.get("fornecedor", dados.get("Fornecedor", ""))

    elif natureza == "conversacional":
        if isinstance(dados, str):
            caminho_lower = dados.lower()
            if any(termo in caminho_lower for termo in ["fiocruz", "ebserh", "ministerio_saude", "comunicacoes_sinteticas"]):
                meta["uf"] = "RJ"

    return meta

def fatiar_texto(texto, max_chars=2000, overlap=200):
    """Divide todo o texto, com sobreposição e avanço garantido."""
    if (
        not isinstance(max_chars, int)
        or not isinstance(overlap, int)
        or max_chars <= 0
        or not 0 <= overlap < max_chars
    ):
        raise ValueError(
            "Use max_chars positivo e 0 <= overlap < max_chars."
        )

    chunks_text = []
    start = 0
    text_len = len(texto)

    while start < text_len:
        end = min(start + max_chars, text_len)
        bloco = texto[start:end]

        if end < text_len:
            last_space = bloco.rfind(" ")
            if last_space > max_chars // 2:
                end = start + last_space
                bloco = texto[start:end]

        if bloco.strip():
            chunks_text.append(bloco.strip())

        if end >= text_len:
            break

        start = max(start + 1, end - overlap)

    return chunks_text

def processar_estruturada(caminho, pasta_saida):
    chunks = []
    if not os.path.exists(caminho): return chunks
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
    registros = dados if isinstance(dados, list) else [dados]

    base_estruturada_pura = []
    for idx, reg in enumerate(registros, 1):
        texto = json.dumps(reg, ensure_ascii=False)
        extras = extrair_metadados_especificos("estruturada", reg)
        chunks.append(criar_chunk_base(texto, os.path.basename(caminho), "contrato", idx, "base_estruturada", "publico", extras))

        registro_limpo = dict(extras)
        registro_limpo["fonte_original"] = caminho
        registro_limpo["texto_integral"] = texto
        base_estruturada_pura.append(registro_limpo)

    os.makedirs(pasta_saida, exist_ok=True)
    with open(f"{pasta_saida}/base_estruturada_normalizada.json", "w", encoding="utf-8") as f:
        json.dump(base_estruturada_pura, f, ensure_ascii=False, indent=4)

    return chunks

# (As funções processar_normativa, processar_agregada e processar_conversacional mantêm-se iguais,
# mas foram omitidas aqui por brevidade para focar apenas na alteração de caminhos)



def processar_normativa(caminho):
    chunks = []
    if not os.path.exists(caminho): return chunks
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except UnicodeDecodeError:
        with open(caminho, "r", encoding="latin-1") as f:
            soup = BeautifulSoup(f, "html.parser")
    texto = soup.get_text(separator=" ")
    artigos = texto.split("Art. ")
    for idx, art in enumerate(artigos[1:], 1):
        extras = extrair_metadados_especificos("normativa")
        chunks.append(criar_chunk_base(f"Art. {art.strip()}", os.path.basename(caminho), "lei", idx, "base_normativa", "publico", extras))
    return chunks


def processar_agregada(caminho, limit=500):
    chunks = []
    if not os.path.exists(caminho): return chunks
    with open(caminho, "r", encoding="utf-8-sig") as f:
        primeira_linha = f.readline()
        delimitador = ';' if ';' in primeira_linha else ','
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delimitador)
        for idx, row in enumerate(reader, 1):
            if idx > limit:
                break
            texto = " | ".join([f"{k}: {v}" for k, v in row.items() if v])
            extras = extrair_metadados_especificos("agregada", row)
            chunks.append(criar_chunk_base(texto, os.path.basename(caminho), "relatorio", idx, "base_agregada", "publico", extras))
    return chunks


def processar_conversacional(caminho):
    chunks = []
    if not os.path.exists(caminho): return chunks
    chunk_idx = 1
    nome_arquivo = os.path.basename(caminho)
    if caminho.endswith(".pdf"):
        with open(caminho, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(reader.pages, 1):
                extract = page.extract_text()
                if extract:
                    blocos = fatiar_texto(extract, max_chars=2000, overlap=200)
                    for bloco in blocos:
                        extras = extrair_metadados_especificos("conversacional", caminho)
                        extras["pagina"] = page_num
                        chunks.append(criar_chunk_base(bloco, nome_arquivo, "ata_reuniao", chunk_idx, "base_conversacional", "restrito", extras))
                        chunk_idx += 1
    elif caminho.endswith(".txt"):
        with open(caminho, "r", encoding="utf-8") as f:
            texto_completo = f.read()
        blocos = fatiar_texto(texto_completo, max_chars=2000, overlap=200)
        for bloco in blocos:
            extras = extrair_metadados_especificos("conversacional", caminho)
            chunks.append(criar_chunk_base(bloco, nome_arquivo, "ata_reuniao", chunk_idx, "base_conversacional", "restrito", extras))
            chunk_idx += 1
    return chunks



def rodar_ingestao_hibrida(
    versao="v3",
    pasta_saida="data/processed",
):
    """Processa as quatro naturezas usando uma única versão do corpus."""
    global inconsistencias_report

    if not re.fullmatch(r"v[0-9]+", versao):
        raise ValueError("Versão inválida. Utilize, por exemplo, v3.")

    pasta_raw = f"data/raw/{versao}"

    caminho_est = (
        f"{pasta_raw}/estruturada/pncp/rj/"
        "pregao_eletronico/2026-03/contratacoes_publicacao.json"
    )
    caminho_norm = (
        f"{pasta_raw}/normativa/federal/"
        "lei_14133_2021/lei_14133_2021.html"
    )
    caminhos_agg = [
        f"{pasta_raw}/agregada/pca_2026_estado_rj.csv",
        f"{pasta_raw}/agregada/itens_pe_038_26_2026.csv",
    ]
    caminhos_conv = [
        f"{pasta_raw}/conversacional/atas/ebserh/2026/ata_00191.pdf",
        f"{pasta_raw}/conversacional/atas/fiocruz/2026/ata_00001.pdf",
        f"{pasta_raw}/conversacional/atas/ministerio_saude/2026/ata_00137.pdf",
        f"{pasta_raw}/conversacional/comunicacoes_sinteticas/"
        "troca_mensagens_material_escritorio_001.txt",
    ]

    caminhos = [
        caminho_est, caminho_norm, *caminhos_agg, *caminhos_conv
    ]
    ausentes = [c for c in caminhos if not os.path.isfile(c)]
    if ausentes:
        raise FileNotFoundError(
            "Corpus incompleto; arquivos ausentes: "
            + ", ".join(ausentes)
        )

    inconsistencias_report = {
        "sem_valor": 0,
        "sem_ano_compra": 0,
        "sem_data_publicacao": 0,
        "sem_id_pncp": 0,
    }

    todos_chunks = []

    def acrescentar(caminho, chunks):
        if not chunks:
            raise RuntimeError(
                f"Nenhum chunk gerado para o arquivo: {caminho}"
            )
        todos_chunks.extend(chunks)

    acrescentar(
        caminho_est,
        processar_estruturada(caminho_est, pasta_saida),
    )
    acrescentar(caminho_norm, processar_normativa(caminho_norm))

    for caminho in caminhos_agg:
        acrescentar(caminho, processar_agregada(caminho, limit=500))

    for caminho in caminhos_conv:
        acrescentar(caminho, processar_conversacional(caminho))

    ids = [c["metadata"]["chunk_id"] for c in todos_chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs de chunks duplicados.")

    os.makedirs(pasta_saida, exist_ok=True)

    with open(
        os.path.join(pasta_saida, "chunks_teste.json"),
        "w", encoding="utf-8",
    ) as arquivo:
        json.dump(todos_chunks, arquivo, ensure_ascii=False, indent=4)

    with open(
        os.path.join(pasta_saida, "inconsistencias_pncp_report.json"),
        "w", encoding="utf-8",
    ) as arquivo:
        json.dump(
            inconsistencias_report, arquivo,
            ensure_ascii=False, indent=4,
        )

    print(
        f"Ingestão {versao} concluída: "
        f"{len(todos_chunks)} chunks em {pasta_saida}."
    )
    return todos_chunks


if __name__ == "__main__":
    rodar_ingestao_hibrida()
