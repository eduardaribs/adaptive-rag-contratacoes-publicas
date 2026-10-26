"""Formato enxuto enviado ao modelo, separado do executor interno."""

from typing import Annotated, Literal
from pydantic import Field

from src.analytical_plan import Contrato, Filtro, Comparacao


class Grupo(Contrato):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$")
    filtros: list[Filtro] = Field(default_factory=list)
    agrupar_por: list[str] = Field(default_factory=list)


class Contar(Grupo):
    operacao: Literal["contar"]


class ContarPreenchidos(Grupo):
    operacao: Literal["contar_preenchidos"]
    campo: str


class ContarDistintos(Grupo):
    operacao: Literal["contar_distintos"]
    campo: str


class Medir(Grupo):
    operacao: Literal["somar", "media", "minimo", "maximo"]
    campo: str


class Listar(Contrato):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$")
    operacao: Literal["listar"]
    filtros: list[Filtro] = Field(default_factory=list)
    campos: list[str] = Field(min_length=1)
    distintos: bool
    limite: int = Field(default=20, ge=1, le=100)
    ordenar_por: str | None = None
    ordem: Literal["crescente", "decrescente"] = "crescente"


class PlanoModelo(Contrato):
    fonte: Literal["itens_pe", "pca"]
    tarefas: list[
        Annotated[
            Contar | ContarPreenchidos | ContarDistintos | Medir | Listar,
            Field(discriminator="operacao"),
        ]
    ] = Field(min_length=1, max_length=12)
    comparacoes: list[Comparacao] = Field(default_factory=list, max_length=6)
    formato: Literal["automatico", "texto", "tabela"] = "automatico"
    pendencias: list[str] = Field(default_factory=list)


class InterpretacaoModelo(Contrato):
    tipo: Literal["plano", "esclarecimento", "documental"]
    mensagem: str
    plano: PlanoModelo | None
    pedido_documental: str | None = None


def decodificar_interpretacao(conteudo):
    """Converte o formato do modelo para o contrato interno validável."""
    if isinstance(conteudo, str):
        conteudo = conteudo.strip()
        linhas = conteudo.splitlines()
        if (
            len(linhas) >= 3
            and linhas[0].strip().lower() in {"```", "```json"}
            and linhas[-1].strip() == "```"
        ):
            conteudo = "\n".join(linhas[1:-1]).strip()

    resposta = InterpretacaoModelo.model_validate_json(conteudo)
    dados = resposta.model_dump()

    if not (dados["pedido_documental"] or "").strip():
        dados["pedido_documental"] = None

    if dados["plano"] is not None:
        for tarefa in dados["plano"]["tarefas"]:
            operacao = tarefa["operacao"]
            if operacao == "contar_preenchidos":
                tarefa["operacao"] = "contar"
                tarefa["distintos"] = False
            elif operacao == "contar_distintos":
                tarefa["operacao"] = "contar"
                tarefa["distintos"] = True

    return dados
