"""Verificação de vínculos explícitos por identificador PNCP."""

import re
from urllib.parse import urlsplit

NATUREZAS = ("estruturada", "agregada", "conversacional", "normativa")


def verificar_vinculos(chunks, *, id_contratacao):
    match = re.fullmatch(
        r"(\d{14})-1-(\d+)/(\d{4})",
        id_contratacao,
    )
    if not match:
        raise ValueError("Identificador PNCP inválido.")

    cnpj, sequencial, ano = match.groups()
    sequencial_numero = int(sequencial)

    padrao_id = re.compile(
        r"(?<![\w-])" + re.escape(id_contratacao) + r"(?![\w/])"
    )
    padrao_url = re.compile(r'https?://[^\s<>"\]]+')

    ids = [
        c.get("chunk_id") or c.get("metadata", {}).get("chunk_id")
        for c in chunks
    ]
    if any(not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("Chunks com IDs ausentes ou duplicados.")

    cobertura = {natureza: 0 for natureza in NATUREZAS}
    correspondencias = {natureza: [] for natureza in NATUREZAS}
    desconhecidos = 0

    for chunk, chunk_id in zip(chunks, ids):
        metadata = chunk.get("metadata") or {}
        natureza = metadata.get("natureza") or chunk.get("natureza")

        if natureza not in cobertura:
            desconhecidos += 1
            continue

        cobertura[natureza] += 1
        texto = str(chunk.get("text") or "")
        vinculo = None

        encontrado = padrao_id.search(texto)
        if encontrado:
            vinculo = {
                "tipo": "id_pncp_exato",
                "evidencia": encontrado.group(),
            }
        else:
            for candidato in padrao_url.findall(texto):
                url = candidato.rstrip(").,;")
                partes = urlsplit(url)
                if partes.hostname not in {"pncp.gov.br", "www.pncp.gov.br"}:
                    continue

                caminho = re.fullmatch(
                    r"/editais/(\d{14})/(\d{4})/(\d+)/?",
                    partes.path,
                )
                if caminho and (
                    caminho.group(1) == cnpj
                    and caminho.group(2) == ano
                    and int(caminho.group(3)) == sequencial_numero
                ):
                    vinculo = {
                        "tipo": "url_pncp_da_contratacao",
                        "evidencia": url,
                    }
                    break

        if vinculo:
            correspondencias[natureza].append({
                "chunk_id": chunk_id,
                "natureza": natureza,
                "fonte": (
                    metadata.get("source_file")
                    or chunk.get("source_file")
                    or chunk.get("fonte")
                ),
                "vinculo": vinculo,
                "trecho": texto,
            })

    return {
        "id_contratacao_pncp": id_contratacao,
        "metodo": "ID PNCP completo ou URL específica do edital",
        "total_chunks_verificados": len(chunks),
        "cobertura_por_natureza": cobertura,
        "chunks_com_natureza_desconhecida": desconhecidos,
        "correspondencias": correspondencias,
        "total_correspondencias": sum(
            len(itens) for itens in correspondencias.values()
        ),
        "observacao": (
            "Ausência de correspondências significa ausência de vínculo "
            "pelos identificadores pesquisados nos chunks carregados. "
            "Não comprova inexistência de documentos relacionados. "
            "Este método não verifica vínculos exclusivamente por conteúdo "
            "ou por outros números de processo."
        ),
    }
