
"""Inicialização Colab com frontend local, testada na Gradio 6.29.0."""
import os

# Localização explícita da raiz do projeto
import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))
if Path.cwd().resolve() != RAIZ_PROJETO:
    raise RuntimeError("Execute este inicializador da raiz do repositório.")

for nome in (
    "PIPELINE_LOG_DIR", "HISTORY_PATH",
    "FEEDBACK_PATH", "GRADIO_SERVER_PORT",
):
    if not os.environ.get(nome):
        raise RuntimeError(f"Configure {nome} antes de iniciar.")

os.environ.setdefault("RAG_DEMO_OFFLINE", "false")
os.environ.setdefault("RERANK_ENABLED", "false")
os.environ.setdefault("LLM_REASONING_EFFORT", "none")
os.environ.setdefault("ROUTER_MAX_TOKENS", "512")


import os
from pathlib import Path
import gradio as gr
from src import obs

obs.PASTA_LOGS = Path(os.environ["PIPELINE_LOG_DIR"])
obs.PASTA_LOGS.mkdir(parents=True, exist_ok=True)


# Usa o frontend instalado, em vez do JavaScript externo do share.html.
import gradio
from gradio import routes
from jinja2 import ChoiceLoader, DictLoader

raiz_gradio = Path(gradio.__file__).resolve().parent
pagina_local = raiz_gradio / "templates/frontend/index.html"
assert pagina_local.is_file(), f"Frontend local ausente: {pagina_local}"

templates = getattr(routes, "templates", None)
assert templates is not None, "Localização dos templates precisa ser conferida."

templates.env.loader = ChoiceLoader([
    DictLoader({
        "frontend/share.html": pagina_local.read_text(encoding="utf-8")
    }),
    templates.env.loader,
])
templates.env.cache.clear()
print("Frontend local selecionado para esta execução.", flush=True)

from app.app import demo

import subprocess
print("Commit carregado:", subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), flush=True)
demo.queue().launch(
    server_name="0.0.0.0",
    server_port=int(os.environ["GRADIO_SERVER_PORT"]),
    share=True,
    show_error=True,
    theme=gr.themes.Soft(),
)
