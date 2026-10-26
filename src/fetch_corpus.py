import shutil
"""Coleta reproduzível do corpus do Grande Desafio RAG."""

import argparse
from pathlib import Path

import yaml


def carregar_manifesto(caminho: Path) -> dict:
    """Lê e valida os campos principais do manifesto."""
    with caminho.open("r", encoding="utf-8") as arquivo:
        dados = yaml.safe_load(arquivo)

    if not isinstance(dados, dict) or not isinstance(dados.get("bases"), list):
        raise ValueError("Manifesto inválido: a seção 'bases' deve ser uma lista.")

    return dados



def verificar_destino_livre(destino: Path) -> None:
    """Impede que uma coleta substitua dados brutos já existentes."""
    if destino.exists():
        raise FileExistsError(
            f"Arquivo já existe e não será sobrescrito: {destino}"
        )


def consultar_pagina_pncp(parametros: dict) -> dict:
    """Consulta uma página, repetindo apenas falhas temporárias."""
    import time
    import requests

    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    max_tentativas = 3

    for tentativa in range(1, max_tentativas + 1):
        try:
            resposta = requests.get(
                url,
                params=parametros,
                timeout=(15, 60),
            )
            resposta.raise_for_status()
            if resposta.status_code == 204:
                raise RuntimeError(
                    "O PNCP retornou HTTP 204 (sem conteúdo) na página "
                    f"{parametros.get('pagina')}. "
                    "Nenhum JSON final será publicado."
                )
            resultado = resposta.json()
        except requests.RequestException as erro:
            status = getattr(getattr(erro, "response", None), "status_code", None)
            temporario = (
                isinstance(erro, (requests.Timeout, requests.ConnectionError))
                or status in (429, 500, 502, 503, 504)
            )

            if not temporario or tentativa == max_tentativas:
                raise RuntimeError(
                    f"Falha na consulta ao PNCP após {tentativa} tentativa(s); "
                    f"nenhum arquivo foi alterado: {erro}"
                ) from erro

            espera = 2 ** (tentativa - 1)
            print(
                f"Falha temporária na página {parametros.get('pagina')}. "
                f"Nova tentativa em {espera} segundo(s) "
                f"({tentativa}/{max_tentativas}).",
                flush=True,
            )
            time.sleep(espera)
            continue
        except ValueError as erro:
            raise RuntimeError(
                "O PNCP retornou uma resposta que não é um JSON válido."
            ) from erro

        if not isinstance(resultado, dict) or not isinstance(
            resultado.get("data"), list
        ):
            raise RuntimeError(
                "Resposta inesperada do PNCP: campo 'data' ausente."
            )

        return resultado

def coletar_paginas_pncp(
    parametros: dict, pasta_progresso: Path, retomar: bool = False
) -> list:
    """Salva páginas completas e exige autorização para retomar."""
    import hashlib
    import json
    import os
    import tempfile

    assinatura = hashlib.sha256(
        json.dumps(parametros, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    pasta = pasta_progresso / assinatura
    configuracao = pasta / "configuracao.json"
    existe_progresso = pasta.exists() and any(pasta.iterdir())

    if existe_progresso and not retomar:
        raise RuntimeError(
            "Há progresso anterior. Confira os checkpoints antes de usar --retomar. "
            "Nenhum arquivo foi alterado."
        )
    if retomar and not existe_progresso:
        raise RuntimeError("Não há progresso anterior para retomar.")

    def salvar_checkpoint(caminho: Path, conteudo) -> None:
        temporario = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".tmp",
                dir=caminho.parent, delete=False
            ) as arquivo:
                temporario = Path(arquivo.name)
                json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            # Não substitui um checkpoint já existente.
            shutil.copy2(temporario, caminho)
        finally:
            if temporario is not None:
                temporario.unlink(missing_ok=True)

    if existe_progresso:
        if not configuracao.is_file():
            raise RuntimeError("Progresso sem configuração; retomada bloqueada.")
        anterior = json.loads(configuracao.read_text(encoding="utf-8"))
        if anterior != parametros:
            raise RuntimeError("Filtros diferentes dos checkpoints; retomada bloqueada.")
    else:
        pasta.mkdir(parents=True, exist_ok=True)
        salvar_checkpoint(configuracao, parametros)

    registros = []
    total_paginas_esperado = None
    total_registros_esperado = None
    pagina = 1

    while True:
        arquivo_pagina = pasta / f"pagina_{pagina:06d}.json"
        if arquivo_pagina.exists():
            resultado = json.loads(arquivo_pagina.read_text(encoding="utf-8"))
            print(f"Página {pagina}: recuperada do progresso salvo.", flush=True)
        else:
            resultado = consultar_pagina_pncp({**parametros, "pagina": pagina})

        if (
            not isinstance(resultado, dict)
            or not isinstance(resultado.get("data"), list)
            or type(resultado.get("totalPaginas")) is not int
            or resultado["totalPaginas"] < 1
            or type(resultado.get("totalRegistros")) is not int
            or resultado["totalRegistros"] < 0
        ):
            raise RuntimeError(f"Resposta ou checkpoint inválido na página {pagina}.")

        total_paginas = resultado["totalPaginas"]
        total_registros = resultado["totalRegistros"]

        if total_paginas_esperado is None:
            total_paginas_esperado = total_paginas
            total_registros_esperado = total_registros
        elif (
            total_paginas != total_paginas_esperado
            or total_registros != total_registros_esperado
        ):
            raise RuntimeError(
                "Paginação ou total de registros mudou; JSON final não será criado."
            )

        if not resultado["data"]:
            raise RuntimeError(f"Página {pagina} vazia; coleta interrompida.")

        if not arquivo_pagina.exists():
            salvar_checkpoint(arquivo_pagina, resultado)
            print(f"Página {pagina}/{total_paginas}: progresso salvo.", flush=True)

        registros.extend(resultado["data"])

        if pagina == total_paginas:
            break
        pagina += 1

    if len(registros) != total_registros_esperado:
        raise RuntimeError(
            f"Contagem divergente: {len(registros)} coletados; "
            f"{total_registros_esperado} informados pelo PNCP."
        )

    ids = [
        item.get("numeroControlePNCP")
        for item in registros if isinstance(item, dict)
    ]
    if (
        len(ids) != len(registros)
        or any(not identificador for identificador in ids)
        or len(set(ids)) != len(ids)
    ):
        raise RuntimeError(
            "Identificadores ausentes ou duplicados; JSON final não será criado."
        )
    # Garante ordem determinística independentemente da ordem retornada pela API.
    registros.sort(key=lambda item: item["numeroControlePNCP"])

    return registros

def executar_fetch(manifesto: dict, raiz: Path, retomar: bool = False) -> None:
    """Coleta a base estruturada sem substituir arquivos existentes."""
    import json
    import os
    import tempfile

    base = next(
        (
            item for item in manifesto["bases"]
            if item.get("base_id") == "estruturada_pncp_rj"
        ),
        None,
    )
    if base is None:
        raise ValueError("Base estruturada não encontrada no manifesto.")

    destino = raiz / base["arquivo_local"]

    # Esta verificação acontece ANTES de qualquer consulta à API.
    verificar_destino_livre(destino)

    filtros = base["selecao_deterministica"]
    parametros = {
        "dataInicial": filtros["dataInicial"],
        "dataFinal": filtros["dataFinal"],
        "codigoModalidadeContratacao": filtros["codigoModalidadeContratacao"],
        "uf": filtros["uf"],
        "tamanhoPagina": 50,
    }

    registros = coletar_paginas_pncp(
        parametros, destino.parent / "_progresso_fetch", retomar=retomar
    )
    if not registros:
        raise RuntimeError("A consulta não retornou registros; nada foi salvo.")

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = None

    try:
        # Grava primeiro em arquivo temporário. Só publica ao terminar.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json.tmp",
            dir=destino.parent,
            delete=False,
        ) as arquivo:
            temporario = Path(arquivo.name)
            json.dump(registros, arquivo, ensure_ascii=False, indent=2)
            arquivo.flush()
            os.fsync(arquivo.fileno())

        # Falha se outro processo tiver criado o destino nesse intervalo.
        os.link(temporario, destino)
        print(f"Coleta concluída: {len(registros)} registros")
        print(f"Arquivo salvo: {destino}")
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)



def main() -> None:
    parser = argparse.ArgumentParser(description="Ferramenta de coleta do corpus")
    parser.add_argument("comando", choices=["inventory", "fetch", "update"])
    parser.add_argument("--manifest", default="corpus_manifest.yaml")
    parser.add_argument("--retomar", action="store_true")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--sources", help="Pasta com as fontes locais")
    argumentos = parser.parse_args()

    caminho_manifesto = Path(argumentos.manifest).resolve()
    manifesto = carregar_manifesto(caminho_manifesto)

    if argumentos.comando == "fetch" and not argumentos.sources:
        executar_fetch(
            manifesto, caminho_manifesto.parent, retomar=argumentos.retomar
        )
        return

    from .corpus_cli import main as corpus_main
    import sys

    sys.argv = [
        sys.argv[0], argumentos.comando,
        "--manifest", str(caminho_manifesto),
        "--version", argumentos.version,
    ] + (["--sources", argumentos.sources] if argumentos.sources else [])
    corpus_main()


if __name__ == "__main__":
    main()
