"""Leitura das fontes autorizadas para o executor analítico."""

import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path

from src.aggregate_query import decimal_csv
from src.analytical_plan import CAMPOS, PlanoAnalitico
from src.analytical_executor import executar_analitico


FONTES = {
    "itens_pe": {
        "arquivo": "data/raw/v3/agregada/itens_pe_038_26_2026.csv",
        "separador": ",",
        "numeros": "decimal",
        "colunas": {campo: campo for campo in CAMPOS["itens_pe"]},
        "observacao": (
            "Itens do arquivo fornecido. Registro de item homologado "
            "não comprova execução, pagamento ou entrega."
        ),
    },
    "pca": {
        "arquivo": "data/raw/v3/agregada/pca_2026_estado_rj.csv",
        "separador": ";",
        "numeros": "br",
        "colunas": {
            "unidade_responsavel": "Unidade Responsável",
            "uasg": "UASG",
            "id_item": "Id do item no PCA",
            "categoria": "Categoria do Item",
            "id_futura_contratacao": "Identificador da Futura Contratação",
            "nome_futura_contratacao": "Nome da Futura Contratação",
            "catalogo": "Catálogo Utilizado",
            "classificacao_catalogo": "Classificação do Catálogo",
            "codigo_classe_grupo": "Código da Classificação Superior (Classe/Grupo)",
            "nome_classe_grupo": "Nome da Classificação Superior (Classe/Grupo)",
            "codigo_pdm": "Código do PDM do Item",
            "nome_pdm": "Nome do PDM do Item",
            "codigo_item": "Código do Item",
            "descricao": "Descrição do Item",
            "unidade_fornecimento": "Unidade de Fornecimento",
            "quantidade_estimada": "Quantidade Estimada",
            "valor_unitario_estimado": "Valor Unitário Estimado (R$)",
            "valor_total_estimado": "Valor Total Estimado (R$)",
            "valor_orcamentario_exercicio": "Valor orçamentário estimado para o exercício (R$)",
            "data_desejada": "Data Desejada",
        },
        "observacao": (
            "Resultados restritos ao arquivo PCA disponibilizado. "
            "Ano e UF associados ao arquivo não são filtros por linha "
            "nem comprovação independente de sua abrangência. "
            "Planejamento não equivale a contratação efetivada."
        ),
    },
}


def _data_iso(valor):
    texto = valor.strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(
            texto.replace("Z", "+00:00")
        ).date().isoformat()
    except ValueError as erro:
        raise ValueError(f"Data não reconhecida: {texto!r}") from erro


def campos_do_plano(plano):
    campos = {f.campo for f in plano.filtros}
    for tarefa in plano.tarefas:
        campos.update(f.campo for f in tarefa.filtros)
        campos.update(tarefa.campos)
        campos.update(tarefa.agrupar_por)
        if tarefa.campo:
            campos.add(tarefa.campo)
        if tarefa.ordenar_por:
            campos.add(tarefa.ordenar_por)
    return campos


def carregar_fonte(fonte, *, campos=None, raiz=None):
    if fonte not in FONTES:
        raise ValueError("Fonte não autorizada.")
    configuracao = FONTES[fonte]
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    caminho = raiz / configuracao["arquivo"]
    conteudo = caminho.read_bytes()
    leitor = csv.DictReader(
        io.StringIO(conteudo.decode("utf-8-sig")),
        delimiter=configuracao["separador"],
    )

    colunas = configuracao["colunas"]
    faltantes = set(colunas.values()) - set(leitor.fieldnames or [])
    if faltantes:
        raise ValueError(f"Colunas ausentes: {sorted(faltantes)}")

    selecionados = set(CAMPOS[fonte]) if campos is None else set(campos)
    if selecionados - set(CAMPOS[fonte]):
        raise ValueError("Campo não autorizado.")

    registros = []
    chaves_itens = set()

    for numero, linha in enumerate(leitor, start=2):
        if None in linha or any(v is None for v in linha.values()):
            raise ValueError(f"Linha CSV malformada: {numero}")

        if fonte == "itens_pe":
            chave = (
                linha["id_contratacao_pncp"].strip(),
                linha["numero_item"].strip(),
            )
            if not all(chave) or chave in chaves_itens:
                raise ValueError("Item com identificador ausente ou duplicado.")
            chaves_itens.add(chave)

        registro = {}
        for campo in selecionados:
            valor = linha[colunas[campo]].strip()
            tipo = CAMPOS[fonte][campo]
            if tipo == "numero":
                valor = decimal_csv(valor, formato=configuracao["numeros"])
            elif tipo == "data":
                valor = _data_iso(valor)
            else:
                valor = valor or None
            registro[campo] = valor
        registros.append(registro)

    return registros, {
        "fonte": fonte,
        "arquivo": str(caminho),
        "sha256": hashlib.sha256(conteudo).hexdigest(),
        "linhas_lidas": len(registros),
        "observacao": configuracao["observacao"],
    }


def executar_fonte(plano, *, raiz=None):
    if isinstance(plano, PlanoAnalitico):
        plano = plano.model_dump()
    plano = PlanoAnalitico.model_validate(plano)
    if plano.pendencias:
        raise ValueError("Plano possui pendências; não executar.")

    registros, proveniencia = carregar_fonte(
        plano.fonte,
        campos=campos_do_plano(plano),
        raiz=raiz,
    )
    resultado = executar_analitico(plano, registros)
    resultado["proveniencia"] = proveniencia
    return resultado
