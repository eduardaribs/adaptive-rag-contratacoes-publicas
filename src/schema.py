"""
schema.py
Responsabilidades:
- Padronizar a saída do roteador.
- Padronizar a saída da recuperação.
- Padronizar as evidências recuperadas.
- Padronizar a resposta final do RAG.
- Validar regras básicas de consistência entre os módulos.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

# Tipos

Rota = Literal[
    "normativa",
    "estruturada",
    "conversacional",
    "agregada",
]

NivelConfianca = Literal[
    "alta",
    "media",
    "baixa",
]

# Filtros da consulta

class QueryFilters(BaseModel):
# Filtros estruturados identificados pelo roteador.

    uf: Optional[str] = None
    ano: Optional[int] = None

    valor_minimo: Optional[float] = None
    valor_maximo: Optional[float] = None

    modalidade: Optional[str] = None
    municipio: Optional[str] = None
    fornecedor: Optional[str] = None

# Tokens

class TokenUsage(BaseModel):
# Contagem de tokens utilizados em uma chamada ao LLM.

    prompt: int = 0
    completion: int = 0
    total: int = 0

# Saida do router

class RouterResult(BaseModel):
# Estrutura retornada pelo router.py.

    query: str
    query_id: str

    routes: List[Rota] = Field(default_factory=list)

    filters: QueryFilters = Field(
        default_factory=QueryFilters
    )

    is_refusal: bool = False
    refusal_reason: Optional[str] = None

    justification: str = ""

    router_fallback: bool = False
    router_error: Optional[str] = None

    stage: str = "roteamento"

    latencia_ms: float = 0.0

    tokens: TokenUsage = Field(
        default_factory=TokenUsage
    )

    modelo: Optional[str] = None

# Evidencias

class SourceEvidence(BaseModel):
# Representa uma evidência recuperada pelo retrieve.py.

    chunk_id: str

    text: str

    rrf_score: float = 0.0
    rerank_score: Optional[float] = None

    retrieval_sources: List[str] = Field(
        default_factory=list
    )

    dense_distance: Optional[float] = None
    bm25_score: Optional[float] = None

    source_file: Optional[str] = None
    doc_type: Optional[str] = None

    sensitivity: str = "publico"

    base_id: Optional[str] = None
    natureza: Optional[str] = None

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )

# Resumo da resuperação

class RetrievalSummary(BaseModel):
# Informações resumidas sobre a recuperação.

    dense_candidates: int = 0
    bm25_candidates: int = 0
    rrf_candidates: int = 0
    returned: int = 0


# Retorno do retrivier

class RetrievalResult(BaseModel):
# Estrutura retornada pelo retrieve.py.

    query: str
    query_id: str

    routes: List[Rota] = Field(
        default_factory=list
    )

    filters: QueryFilters = Field(
        default_factory=QueryFilters
    )

    router_justification: Optional[str] = None

    router_fallback: bool = False

    is_refusal: bool = False

    refusal_reason: Optional[str] = None

    evidences: List[SourceEvidence] = Field(
        default_factory=list
    )

    retrieval_summary: RetrievalSummary = Field(
        default_factory=RetrievalSummary
    )

    stage: str = "fusao_rrf"

    latencia_ms: float = 0.0

    @model_validator(mode="after")
    def validar_recusa(self):
    # Uma recuperação marcada como recusa não deve fornecer evidências para geração.

        if self.is_refusal and self.evidences:
            raise ValueError(
                "RetrievalResult com is_refusal=True "
                "não pode possuir evidências."
            )

        return self

# Resposta final do RAG

class RAGResponse(BaseModel):
# Contrato final da resposta produzida pelo generate.py.

    query: str
    query_id: str

    answer: str

    confidence_level: NivelConfianca = "baixa"

    sources_used: List[SourceEvidence] = Field(
        default_factory=list
    )

    is_refusal: bool = False

    refusal_reason: Optional[str] = None

    tokens: TokenUsage = Field(
        default_factory=TokenUsage
    )

    modelo: Optional[str] = None

    latencia_ms: float = 0.0

    stage: str = "geracao"

    @model_validator(mode="after")
    def validar_resposta(self):
    #    Valida regras básicas do contrato final.

        if self.is_refusal and self.sources_used:
            raise ValueError(
                "RAGResponse com is_refusal=True "
                "não pode possuir fontes."
            )

        if self.is_refusal and not self.refusal_reason:
            raise ValueError(
                "RAGResponse com is_refusal=True "
                "deve possuir refusal_reason."
            )

        if not self.answer.strip():
            raise ValueError(
                "A resposta não pode estar vazia."
            )

        return self