import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional
from zoneinfo import ZoneInfo


FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")
PASTA_LOGS = Path(
    os.getenv("PIPELINE_LOG_DIR", "logs")
)

STAGES_VALIDOS = {
    'consulta_agregada',
    'feedback',
    'fusao_rrf',
    'geracao',
    'query_analysis',
    'rerank',
    'retrieval_bm25',
    'retrieval_denso',
    'roteamento',
    'validacao',
}

# Etapa de execução sobre a base estruturada completa.
STAGES_VALIDOS.add("consulta_estruturada")

_lock_escrita = threading.Lock()


def novo_run_id() -> str:
    """
    Cria o identificador utilizado em todas as etapas da mesma consulta.
    """
    return uuid.uuid4().hex[:8]


def novo_query_id() -> str:
    """
    Cria um identificador para a pergunta processada.
    """
    return f"q_{uuid.uuid4().hex[:8]}"


def timestamp_atual() -> str:
    """
    Retorna data e hora no fuso de São Paulo, em formato ISO 8601.
    """
    return datetime.now(FUSO_HORARIO).isoformat(
        timespec="seconds"
    )


def caminho_log_atual() -> Path:
    """
    Define o arquivo diário de logs.
    """
    data = datetime.now(FUSO_HORARIO).strftime("%Y-%m-%d")

    return PASTA_LOGS / f"pipeline-{data}.jsonl"


def normalizar_tokens(
    tokens: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """
    Garante o formato padrão do campo tokens.
    """
    tokens = tokens or {}

    prompt = int(
        tokens.get(
            "prompt",
            tokens.get("prompt_tokens", 0),
        )
        or 0
    )

    completion = int(
        tokens.get(
            "completion",
            tokens.get("completion_tokens", 0),
        )
        or 0
    )

    total = int(
        tokens.get(
            "total",
            tokens.get(
                "total_tokens",
                prompt + completion,
            ),
        )
        or 0
    )

    return {
        "prompt": prompt,
        "completion": completion,
        "total": total,
    }


def extrair_tokens_resposta(
    resposta: Any,
) -> Dict[str, int]:
    """
    Extrai o uso de tokens de uma resposta compatível com OpenAI.
    """
    usage = getattr(resposta, "usage", None)

    if usage is None:
        return normalizar_tokens()

    return normalizar_tokens(
        {
            "prompt_tokens": getattr(
                usage,
                "prompt_tokens",
                0,
            ),
            "completion_tokens": getattr(
                usage,
                "completion_tokens",
                0,
            ),
            "total_tokens": getattr(
                usage,
                "total_tokens",
                0,
            ),
        }
    )


def registrar_evento(
    *,
    run_id: str,
    query_id: str,
    stage: str,
    status: str,
    latencia_ms: float,
    input_data: Any,
    output_data: Any,
    tokens: Optional[Dict[str, Any]] = None,
    modelo: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Registra uma etapa do pipeline no arquivo JSONL diário.
    """
    if stage not in STAGES_VALIDOS:
        raise ValueError(
            f"Stage inválido: {stage}. "
            f"Valores permitidos: {sorted(STAGES_VALIDOS)}"
        )

    if not run_id:
        raise ValueError("run_id é obrigatório.")

    if not query_id:
        raise ValueError("query_id é obrigatório.")

    evento = {
        "ts": timestamp_atual(),
        "run_id": run_id,
        "query_id": query_id,
        "stage": stage,
        "status": status,
        "latencia_ms": round(float(latencia_ms), 2),
        "input": input_data,
        "output": output_data,
        "tokens": normalizar_tokens(tokens),
        "modelo": modelo,
        "extra": extra or {},
    }

    caminho = caminho_log_atual()
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    linha = json.dumps(
        evento,
        ensure_ascii=False,
        default=str,
    )

    with _lock_escrita:
        with caminho.open(
            "a",
            encoding="utf-8",
        ) as arquivo:
            arquivo.write(linha + "\n")

    return evento


@contextmanager
def observar_etapa(
    *,
    run_id: str,
    query_id: str,
    stage: str,
    input_data: Any,
    modelo: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Context manager para medir uma etapa e registrar sucesso ou erro.

    Exemplo:

        with observar_etapa(...) as observacao:
            resultado = executar()
            observacao["output"] = resultado
    """
    inicio = time.perf_counter()

    observacao: Dict[str, Any] = {
        "output": None,
        "tokens": None,
        "extra": extra or {},
    }

    try:
        yield observacao

    except Exception as erro:
        latencia = (
            time.perf_counter() - inicio
        ) * 1000

        registrar_evento(
            run_id=run_id,
            query_id=query_id,
            stage=stage,
            status="erro",
            latencia_ms=latencia,
            input_data=input_data,
            output_data={
                "erro": type(erro).__name__,
                "mensagem": str(erro),
            },
            tokens=observacao.get("tokens"),
            modelo=modelo,
            extra=observacao.get("extra"),
        )

        raise

    else:
        latencia = (
            time.perf_counter() - inicio
        ) * 1000

        registrar_evento(
            run_id=run_id,
            query_id=query_id,
            stage=stage,
            status="ok",
            latencia_ms=latencia,
            input_data=input_data,
            output_data=observacao.get("output"),
            tokens=observacao.get("tokens"),
            modelo=modelo,
            extra=observacao.get("extra"),
        )
