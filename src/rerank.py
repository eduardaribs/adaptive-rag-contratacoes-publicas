"""Rerank opcional por cross-encoder local; fallback explícito para RRF."""

import logging
import os
import time
from contextvars import ContextVar
from functools import lru_cache
import math

logger = logging.getLogger(__name__)

RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").lower() == "true"
RERANK_URL = os.getenv("RERANK_URL", "http://localhost/rerank")
RERANK_AUTH = os.getenv("RERANK_AUTH", "")
RERANK_MODEL = os.getenv("RERANK_MODEL", "modelo-padrao")
RERANK_TIMEOUT = int(os.getenv("RERANK_TIMEOUT", "5"))
MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", "20"))
TOP_K = int(os.getenv("TOP_K", "3"))

MODELO_LOCAL_PADRAO = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_ultima_execucao = ContextVar("ultima_execucao_rerank", default=None)


def ultimo_resultado():
    return dict(_ultima_execucao.get() or {})


def _registrar(status, aplicado, inicio, **detalhes):
    evento = {
        "event": "rerank",
        "status": status,
        "applied": aplicado,
        "latency_ms": round((time.perf_counter() - inicio) * 1000, 2),
        **detalhes,
    }
    _ultima_execucao.set(evento)
    if status in {
        "not_implemented_fallback_rrf",
        "failed_fallback_rrf",
    }:
        logger.warning(evento)
    else:
        logger.info(evento)


@lru_cache(maxsize=1)
def _carregar_modelo(nome, revisao, cache):
    # Dependências opcionais: não são importadas no modo desativado.
    import torch
    from sentence_transformers import CrossEncoder

    torch.set_num_threads(2)
    opcoes = {
        "device": "cpu",
        "max_length": 512,
        "trust_remote_code": False,
    }
    if revisao:
        opcoes["revision"] = revisao
    if cache:
        opcoes["cache_folder"] = cache
    return CrossEncoder(nome, **opcoes)


def executar_rerank(pergunta, candidatos_rrf):
    inicio = time.perf_counter()
    candidatos = list(candidatos_rrf)
    fallback = [(candidato, None) for candidato in candidatos]

    if not candidatos:
        _registrar("skipped_empty_list", False, inicio)
        return []

    if not RERANK_ENABLED:
        _registrar("disabled_fallback_rrf", False, inicio)
        return fallback

    if os.getenv("RERANK_BACKEND", "").lower() != "local":
        _registrar("not_implemented_fallback_rrf", False, inicio)
        return fallback

    nome = (
        MODELO_LOCAL_PADRAO
        if RERANK_MODEL == "modelo-padrao"
        else RERANK_MODEL
    )
    revisao = os.getenv("RERANK_REVISION") or None
    cache = os.getenv("RERANK_CACHE_DIR") or None
    limite = max(1, min(MAX_CANDIDATES, 200))
    selecionados = candidatos[:limite]

    try:
        if not isinstance(pergunta, str) or not pergunta.strip():
            raise ValueError("Pergunta vazia.")
        if any(
            not isinstance(item.get("text"), str)
            or not item["text"].strip()
            for item in selecionados
        ):
            raise ValueError("Candidato sem texto.")

        modelo = _carregar_modelo(nome, revisao, cache)
        scores = modelo.predict(
            [(pergunta, item["text"]) for item in selecionados],
            batch_size=4,
            show_progress_bar=False,
        )
        valores = [float(score) for score in scores]

        if len(valores) != len(selecionados):
            raise ValueError("Quantidade de scores incompatível.")
        if not all(math.isfinite(score) for score in valores):
            raise ValueError("Score não finito.")

        # Empates preservam a ordem RRF.
        ordem = sorted(
            range(len(valores)),
            key=lambda indice: (-valores[indice], indice),
        )
        resultado = [
            (selecionados[indice], valores[indice])
            for indice in ordem
        ]
        # Preserva candidatos além do limite, sem atribuir scores fictícios.
        resultado.extend(
            (item, None) for item in candidatos[limite:]
        )

        _registrar(
            "applied_local_cross_encoder", True, inicio,
            model=nome,
            revision=revisao,
            candidates_scored=len(selecionados),
            candidates_preserved_unscored=len(candidatos) - len(selecionados),
            device="cpu",
            max_length=512,
        )
        return resultado

    except Exception as erro:
        _registrar(
            "failed_fallback_rrf", False, inicio,
            model=nome,
            error_type=type(erro).__name__,
            error=str(erro),
        )
        return fallback
