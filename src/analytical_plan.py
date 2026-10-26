"""Plano analítico validado, independente da redação da pergunta."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


# Nomes públicos para o planejador; tipos usados pelo executor.
CAMPOS = {
    "itens_pe": {
        "id_contratacao_pncp": "texto",
        "numero_item": "numero",
        "situacao_item": "texto",
        "quantidade_homologada": "numero",
        "valor_unitario_homologado": "numero",
        "valor_total_homologado": "numero",
        "fornecedor": "texto",
        "data_homologacao": "data",
        "url_fonte": "texto",
    },
    "pca": {
        "unidade_responsavel": "texto",
        "uasg": "texto",
        "id_item": "texto",
        "categoria": "texto",
        "id_futura_contratacao": "texto",
        "nome_futura_contratacao": "texto",
        "catalogo": "texto",
        "classificacao_catalogo": "texto",
        "codigo_classe_grupo": "texto",
        "nome_classe_grupo": "texto",
        "codigo_pdm": "texto",
        "nome_pdm": "texto",
        "codigo_item": "texto",
        "descricao": "texto",
        "unidade_fornecimento": "texto",
        "quantidade_estimada": "numero",
        "valor_unitario_estimado": "numero",
        "valor_total_estimado": "numero",
        "valor_orcamentario_exercicio": "numero",
        "data_desejada": "data",
    },
}


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Filtro(Contrato):
    campo: str
    operador: Literal[
        "igual", "diferente", "contem", "em",
        "maior", "maior_igual", "menor", "menor_igual",
    ]
    # Valores numéricos são strings para evitar perda de precisão.
    valor: str | list[str]

    @model_validator(mode="after")
    def validar_valor(self):
        if self.operador == "em":
            if not isinstance(self.valor, list) or not self.valor:
                raise ValueError("O operador em exige uma lista não vazia.")
        elif not isinstance(self.valor, str):
            raise ValueError("Este operador exige um valor textual.")
        return self


class Tarefa(Contrato):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$")
    operacao: Literal[
        "contar", "somar", "media", "minimo", "maximo", "listar",
    ]
    campo: str | None = None
    filtros: list[Filtro] = Field(default_factory=list)
    agrupar_por: list[str] = Field(default_factory=list)
    campos: list[str] = Field(default_factory=list)
    limite: int = Field(default=20, ge=1, le=100)
    distintos: bool = False
    ordenar_por: str | None = None
    ordem: Literal["crescente", "decrescente"] = "crescente"

    @field_validator("campo", "ordenar_por", mode="before")
    @classmethod
    def normalizar_opcionais(cls, valor):
        if isinstance(valor, str):
            return valor.strip() or None
        return valor



class Comparacao(Contrato):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$")
    operacao: Literal["diferenca", "razao", "percentual"]
    esquerda: str
    direita: str


class PlanoAnalitico(Contrato):
    fonte: Literal["itens_pe", "pca"]
    filtros: list[Filtro] = Field(default_factory=list)
    tarefas: list[Tarefa] = Field(min_length=1, max_length=12)
    comparacoes: list[Comparacao] = Field(default_factory=list, max_length=6)
    formato: Literal["automatico", "texto", "tabela"] = "automatico"
    pendencias: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_plano(self):
        campos = CAMPOS[self.fonte]
        ids = [t.id for t in self.tarefas] + [
            c.id for c in self.comparacoes
        ]
        if len(ids) != len(set(ids)):
            raise ValueError("Identificadores de resultados duplicados.")

        filtros = list(self.filtros)
        tarefas = {t.id: t for t in self.tarefas}

        for tarefa in self.tarefas:
            utilizados = (
                tarefa.agrupar_por + tarefa.campos
                + ([tarefa.campo] if tarefa.campo else [])
                + ([tarefa.ordenar_por] if tarefa.ordenar_por else [])
            )
            indisponiveis = sorted(set(utilizados) - set(campos))
            if indisponiveis:
                raise ValueError(
                    f"Tarefa {tarefa.id}: campos indisponíveis na fonte "
                    f"{self.fonte}: {', '.join(indisponiveis)}. "
                    f"Campos permitidos: {', '.join(campos)}."
                )

            if tarefa.operacao in {"somar", "media", "minimo", "maximo"}:
                if campos.get(tarefa.campo) != "numero":
                    raise ValueError("A operação exige um campo numérico.")

            if tarefa.operacao == "listar":
                if not tarefa.campos or tarefa.agrupar_por:
                    raise ValueError("Listagem exige campos e não aceita agrupamento.")
                if tarefa.campo:
                    raise ValueError("Parâmetros incompatíveis com listagem.")
                if (
                    tarefa.distintos and tarefa.ordenar_por
                    and tarefa.ordenar_por not in tarefa.campos
                ):
                    raise ValueError(
                        "Listagem distinta exige ordenar por campo exibido."
                    )
            elif tarefa.campos or tarefa.ordenar_por:
                raise ValueError("Campos de exibição e ordenação exigem listagem.")

            if tarefa.distintos and tarefa.operacao != "listar" and (
                tarefa.operacao != "contar" or not tarefa.campo
            ):
                raise ValueError("Contagem distinta exige campo.")
            filtros.extend(tarefa.filtros)

        for filtro in filtros:
            if filtro.campo not in campos:
                raise ValueError("Filtro usa campo não disponível.")
            tipo = campos[filtro.campo]
            if filtro.operador == "contem" and tipo != "texto":
                raise ValueError("Contem exige campo textual.")
            if filtro.operador in {
                "maior", "maior_igual", "menor", "menor_igual"
            } and tipo not in {"numero", "data"}:
                raise ValueError("Comparação ordenada exige número ou data.")

        for comparacao in self.comparacoes:
            for referencia in (comparacao.esquerda, comparacao.direita):
                if referencia not in tarefas:
                    raise ValueError("Comparação referencia tarefa inexistente.")
                tarefa = tarefas[referencia]
                if tarefa.operacao == "listar" or tarefa.agrupar_por:
                    raise ValueError("Comparação exige resultados escalares.")

        return self

    @model_validator(mode="after")
    def validar_escopos_e_grandezas(self):
        import unicodedata
        from decimal import Decimal

        def canonico(campo, valor):
            if CAMPOS[self.fonte][campo] == "numero":
                numero = Decimal(valor)
                if not numero.is_finite():
                    raise ValueError("Filtro numérico não finito.")
                return numero
            return "".join(
                c for c in unicodedata.normalize("NFD", valor.strip().casefold())
                if unicodedata.category(c) != "Mn"
            )

        def conferir_conjuncao(filtros):
            por_campo = {}
            for filtro in filtros:
                por_campo.setdefault(filtro.campo, []).append(filtro)

            for campo, condicoes in por_campo.items():
                permitidos = None
                proibidos = set()
                for filtro in condicoes:
                    if filtro.operador == "igual":
                        conjunto = {canonico(campo, filtro.valor)}
                    elif filtro.operador == "em":
                        conjunto = {
                            canonico(campo, valor) for valor in filtro.valor
                        }
                    elif filtro.operador == "diferente":
                        proibidos.add(canonico(campo, filtro.valor))
                        continue
                    else:
                        continue

                    permitidos = (
                        conjunto if permitidos is None
                        else permitidos & conjunto
                    )

                if permitidos is not None and not (permitidos - proibidos):
                    raise ValueError(
                        f"Filtros contraditórios para {campo}. "
                        "Filtros globais são condições simultâneas. "
                        "Grupos comparados devem usar filtros em tarefas separadas."
                    )

        conferir_conjuncao(self.filtros)
        for tarefa in self.tarefas:
            conferir_conjuncao([*self.filtros, *tarefa.filtros])

        tarefas = {t.id: t for t in self.tarefas}

        def grandeza(tarefa):
            if tarefa.operacao == "contar":
                return (
                    ("valores_distintos", tarefa.campo)
                    if tarefa.distintos else ("registros", self.fonte)
                )
            return ("valor_do_campo", tarefa.campo)

        for comparacao in self.comparacoes:
            # Razões podem produzir uma grandeza derivada:
            # por exemplo, valor monetário por registro.
            # Diferenças e percentuais exigem grandezas compatíveis.
            if (
                comparacao.operacao in {"diferenca", "percentual"}
                and grandeza(tarefas[comparacao.esquerda]) != grandeza(
                    tarefas[comparacao.direita]
                )
            ):
                raise ValueError(
                    "Comparação entre grandezas incompatíveis: "
                    "contagem de registros, quantidade física e valores "
                    "de campos diferentes não são intercambiáveis."
                )
        return self
