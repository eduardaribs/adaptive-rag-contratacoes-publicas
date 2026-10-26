"""Interface para consultas estruturadas e documentais."""

import os
import sys

import gradio as gr

from app.pipeline_adapter import executar_pipeline
from app.history_store import (
    salvar_consulta,
    listar_consultas,
    carregar_consulta,
)
from app.interface_results import (
    feedback_da_consulta,
    mudar_pagina,
    status_consulta,
    tabela_consulta,
)


TITULO = "Contratações Públicas do Estado do Rio de Janeiro"

DESCRICAO = (
    "Contagens e listagens sobre a base disponível "
    "e respostas documentais com fontes."
)


def apresentar(resultado):
    executado = resultado.get("executado", False)
    estrategia = resultado.get("estrategia")

    lista = (
        resultado.get("operacao") == "listar"
        and executado
    )
    agregada = (
        estrategia == "consulta_agregada"
        and executado
    )
    analitica = estrategia in {
        "consulta_analitica", "combinada_analitica"
    }
    tabelas_analiticas = resultado.get("tabelas_analiticas") or []
    resposta_exibida = resultado.get("answer", "")
    tabelas_embutidas = bool(tabelas_analiticas) and all(
        isinstance(tabela, dict)
        and isinstance(tabela.get("markdown"), str)
        and bool(tabela["markdown"].strip())
        and tabela["markdown"] in resposta_exibida
        for tabela in tabelas_analiticas
    )
    mostrar_tabela = lista or agregada or (
        analitica
        and executado
        and bool(resultado.get("campos"))
        and not tabelas_embutidas
    )

    deterministica = estrategia in {
        "consulta_estruturada", "consulta_agregada",
        "consulta_analitica", "combinada_analitica"
    }

    pagina = resultado.get("pagina") or 1
    paginas = resultado.get("total_paginas", 0)

    detalhes = {
        "modo_demonstracao": resultado.get("modo_demonstracao"),
        "roteamento_demonstracao": resultado.get("roteamento_demonstracao"),
        "commit_demonstracao": resultado.get("commit_demonstracao"),
        "versao_artefatos": resultado.get("versao_artefatos"),
        "plano": resultado.get("plano", {}),
        "interpretacao_analitica": resultado.get("interpretacao_analitica"),
        "calculo_analitico": resultado.get("calculo_analitico"),
        "proveniencia_calculo": resultado.get("proveniencia_calculo"),
        "tabelas_analiticas": resultado.get("tabelas_analiticas", []),
        "fontes": resultado.get("fontes", []),
        "fontes_estruturadas": resultado.get("fontes_estruturadas", []),
        "fontes_agregadas": resultado.get("fontes_agregadas", []),
        "fontes_recuperadas": resultado.get("fontes_recuperadas", []),
        "fontes_citadas": resultado.get("fontes_citadas", []),
        "documental_query_id": resultado.get("documental_query_id"),
        "documental_run_id": resultado.get("documental_run_id"),
        "paginacao_run_id": resultado.get("paginacao_run_id"),
        "referencias": resultado.get("referencias", []),
        "evidencias": resultado.get("evidences", []),
        "criterio_tecnologia": resultado.get("criterio_tecnologia"),
        "resumo_tecnologia": resultado.get("resumo_tecnologia"),
        "classificacoes_tecnologia": resultado.get(
            "classificacoes_tecnologia", []
        ),
        "verificacao_vinculos": resultado.get("verificacao_vinculos"),
        "total_chunks_verificados": resultado.get(
            "total_chunks_verificados"
        ),
    }

    return (
        resultado.get("answer", ""),
        gr.update(
            value=tabela_consulta(resultado),
            visible=mostrar_tabela,
        ),
        gr.update(visible=lista),
        gr.update(interactive=lista and pagina > 1),
        gr.update(interactive=lista and pagina < paginas),
        ", ".join(resultado.get("routes", [])),
        resultado.get("filters", {}),
        detalhes,
        (
            "**Demonstração offline — plano local predefinido; "
            "sem roteador LLM ou geração.**\n\n"
            if resultado.get("modo_demonstracao") == "offline" else ""
        ) + status_consulta(resultado),
        resultado,
        None,
        "",
        "",
        gr.update(interactive=not deterministica),
    )


def executar(pergunta, top_k, progress=gr.Progress()):
    try:
        resultado = executar_pipeline(
            pergunta,
            top_k,
            on_progress=lambda valor, texto: progress(
                valor,
                desc=texto,
            ),
        )

        # Falha no histórico não deve descartar uma resposta pronta.
        try:
            salvar_consulta(resultado)
        except Exception:
            gr.Warning(
                "A resposta foi concluída, mas não foi salva no histórico."
            )

        return apresentar(resultado)

    except Exception as erro:
        return apresentar({
            "answer": (
                "Não foi possível concluir a consulta: "
                f"{erro}"
            ),
        })


def navegar(resultado, direcao):
    try:
        return apresentar(
            mudar_pagina(resultado, direcao)
        )

    except Exception as erro:
        gr.Warning(str(erro))
        return apresentar(resultado or {})


def limpar_interface():
    return (
        "",
        *apresentar({
            "answer": "Digite uma pergunta para iniciar.",
        }),
    )



def atualizar_historico():
    """Lista consultas persistidas no ambiente da aplicação."""
    escolhas = [
        (
            f"{item['criado_em']} | {item['pergunta'][:100]} "
            f"| {item['run_id']}",
            item["run_id"],
        )
        for item in listar_consultas()
    ]
    return gr.update(choices=escolhas, value=None)


def abrir_historico(run_id):
    """Reapresenta o registro original sem executar consulta."""
    resultado = carregar_consulta(run_id)
    if resultado is None:
        raise gr.Error("Selecione uma consulta salva disponível.")
    return (resultado["query"], *apresentar(resultado))


def criar_interface():
    with gr.Blocks(title=TITULO) as interface:
        gr.Markdown(f"# {TITULO}")
        gr.Markdown(DESCRICAO)

        if os.getenv("RAG_DEMO_OFFLINE", "false").lower() == "true":
            from app.offline_demo import PERGUNTAS
            gr.Markdown(
                "**Modo de demonstração offline:** cálculos reais sobre "
                "arquivos locais, com planos predefinidos. "
                "Não avalia o roteador LLM nem a geração documental."
            )
            gr.Markdown(
                "**Commit da demonstração:** `"
                + os.getenv("RAG_DEMO_COMMIT", "não informado") + "`"
            )

        gr.Markdown(
            "A quantidade de evidências vale apenas para "
            "consultas documentais. Não limita contagens "
            "ou listagens. O progresso indica etapas, "
            "não uma estimativa exata do tempo restante."
        )

        contexto = gr.State({})

        pergunta = gr.Textbox(
            label="Pergunta",
            lines=3,
            placeholder=(
                "Selecione uma das perguntas da demonstração abaixo."
                if os.getenv("RAG_DEMO_OFFLINE", "false").lower() == "true"
                else "Quantas contratações têm ano da compra 2026?"
            ),
        )

        if os.getenv("RAG_DEMO_OFFLINE", "false").lower() == "true":
            gr.Examples(
                examples=[[texto] for texto in PERGUNTAS.values()],
                inputs=[pergunta],
                label="Perguntas da demonstração",
            )

        top_k = gr.Slider(
            minimum=1,
            maximum=5,
            value=3,
            step=1,
            label="Evidências para consultas documentais",
        )

        with gr.Row():
            consultar = gr.Button(
                "Consultar",
                variant="primary",
            )
            limpar = gr.Button("Limpar")

        resposta = gr.Markdown(
            "Digite uma pergunta para iniciar."
        )

        tabela = gr.Dataframe(
            headers=None,
            value=[],
            interactive=False,
            visible=False,
            label="Registros da página",
        )

        with gr.Row(visible=False) as paginacao:
            anterior = gr.Button(
                "Página anterior",
                interactive=False,
            )
            proxima = gr.Button(
                "Próxima página",
                interactive=False,
            )

        status = gr.Markdown()

        with gr.Accordion("Histórico de consultas", open=False):
            gr.Markdown(
                "Consultas salvas neste ambiente da aplicação. "
                "Abrir um registro apresenta a resposta original, "
                "sem consultar novamente o modelo. "
                "Os resultados podem corresponder a versões anteriores "
                "dos dados. O histórico é compartilhado entre quem "
                "tem acesso a esta instância."
            )
            consulta_salva = gr.Dropdown(
                choices=[],
                label="Consulta salva",
                interactive=True,
            )
            with gr.Row():
                atualizar_salvas = gr.Button("Atualizar histórico")
                abrir_salva = gr.Button("Abrir consulta salva")

        with gr.Accordion(
            "Avalie esta resposta",
            open=False,
        ):
            avaliacao = gr.Radio(
                choices=["Útil", "Não útil"],
                label="Avaliação",
                value=None,
            )
            comentario = gr.Textbox(
                label="Comentário opcional",
                lines=2,
            )
            enviar = gr.Button("Enviar feedback")
            confirmacao = gr.Markdown()

        with gr.Accordion(
            "Plano fontes e evidências",
            open=False,
        ):
            rotas = gr.Textbox(
                label="Bases selecionadas",
                interactive=False,
            )
            filtros = gr.JSON(
                label="Filtros aplicados",
            )
            detalhes = gr.JSON(
                label="Plano fontes referências e evidências",
            )

        saidas = [
            resposta,
            tabela,
            paginacao,
            anterior,
            proxima,
            rotas,
            filtros,
            detalhes,
            status,
            contexto,
            avaliacao,
            comentario,
            confirmacao,
            top_k,
        ]

        opcoes = {
            "concurrency_id": "consultas",
            "concurrency_limit": 1,
        }

        clique = consultar.click(
            fn=executar,
            inputs=[pergunta, top_k],
            outputs=saidas,
            api_name="consultar",
            **opcoes,
        )

        # Atualiza a lista após a consulta e seu salvamento.
        clique.success(
            fn=atualizar_historico,
            outputs=[consulta_salva],
            **opcoes,
        )

        enter = pergunta.submit(
            fn=executar,
            inputs=[pergunta, top_k],
            outputs=saidas,
            **opcoes,
        )

        # Atualiza a lista após a consulta e seu salvamento.
        enter.success(
            fn=atualizar_historico,
            outputs=[consulta_salva],
            **opcoes,
        )

        volta = anterior.click(
            fn=lambda resultado: navegar(resultado, -1),
            inputs=[contexto],
            outputs=saidas,
            **opcoes,
        )

        avanca = proxima.click(
            fn=lambda resultado: navegar(resultado, 1),
            inputs=[contexto],
            outputs=saidas,
            **opcoes,
        )

        feedback = enviar.click(
            fn=feedback_da_consulta,
            inputs=[contexto, avaliacao, comentario],
            outputs=[confirmacao],
            **opcoes,
        )

        atualizar_salvas.click(
            fn=atualizar_historico,
            outputs=[consulta_salva],
            **opcoes,
        )
        abertura = abrir_salva.click(
            fn=abrir_historico,
            inputs=[consulta_salva],
            outputs=[pergunta, *saidas],
            **opcoes,
        )

        # Permite escolher evidências para uma nova pergunta.
        pergunta.input(
            fn=lambda: gr.update(interactive=True),
            outputs=[top_k],
            queue=False,
        )

        limpar.click(
            fn=limpar_interface,
            outputs=[pergunta, *saidas],
            queue=False,
            cancels=[clique, enter, volta, avanca, feedback, abertura],
        )

    return interface


demo = criar_interface()


if __name__ == "__main__":
    demo.queue().launch(
        server_name=os.getenv(
            "GRADIO_SERVER_NAME",
            "0.0.0.0",
        ),
        server_port=int(
            os.getenv("GRADIO_SERVER_PORT", "7860")
        ),
        share="google.colab" in sys.modules,
        show_error=True,
        theme=gr.themes.Soft(),
    )
