import gradio as gr
import pandas as pd
import datetime

# ============================================================
# 1. LLM SIMULADO
# ============================================================
def corrigir_requisito(texto):
    texto = str(texto).strip()

    if "track progress" in texto.lower():
        return ("The system shall track project progress based on defined milestones "
                "and completed tasks, providing real-time updates and displaying "
                "completion percentage on the dashboard.")

    return "The system shall " + texto.lower()


# ============================================================
# 2. INICIAR (CORRIGIDO)
# ============================================================
def iniciar(file):

    if file is None:
        return "⚠️ Carregue um ficheiro", "", "", "", "", None, [], 0

    try:
        # ✅ leitura correta no Gradio
        df = pd.read_csv(file.name) if file.name.endswith(".csv") else pd.read_excel(file.name)
    except Exception as e:
        return f"❌ Erro ao ler ficheiro: {e}", "", "", "", "", None, [], 0

    # normalizar colunas
    df.columns = df.columns.str.lower().str.strip()

    print("COLUNAS:", df.columns.tolist())

    # ====================================================
    # 🔥 MAPEAMENTO ROBUSTO
    # ====================================================
    col_context = None
    col_tipo = None
    col_subtipo = None

    for col in df.columns:

        if col_context is None and any(x in col for x in ["requirement", "text", "description"]):
            col_context = col

        if col_tipo is None and any(x in col for x in ["class", "type", "classe", "fr"]):
            col_tipo = col

        if col_subtipo is None and any(x in col for x in ["sub", "category", "level"]):
            col_subtipo = col

    print("MAPEAMENTO:", col_context, col_tipo, col_subtipo)

    if col_context is None:
        return "❌ Não encontrou coluna de requisito", "", "", "", "", None, [], 0

    # ✅ preencher corretamente
    df["context"] = df[col_context]

    df["tipo"] = df[col_tipo] if col_tipo else ""
    df["subtipo"] = df[col_subtipo] if col_subtipo else ""

    # limpar NaN
    df["tipo"] = df["tipo"].fillna("").astype(str)
    df["subtipo"] = df["subtipo"].fillna("").astype(str)

    # novos campos
    df["context_final"] = ""
    df["status"] = ""
    df["timestamp"] = ""

    tasks = df.to_dict("records")
    idx = 0

    t = tasks[0]

    return (
        f"Tarefa 1/{len(tasks)}",
        t["context"],
        t["tipo"],
        t["subtipo"],
        "",
        None,
        tasks,
        idx
    )


# ============================================================
# 3. APROVAR
# ============================================================
def aprovar(tasks, idx):

    tasks[idx]["context_final"] = tasks[idx]["context"]
    tasks[idx]["status"] = "aprovado"
    tasks[idx]["timestamp"] = str(datetime.datetime.now())

    return proxima(tasks, idx)


# ============================================================
# 4. REJEITAR
# ============================================================
def rejeitar(tasks, idx):

    tasks[idx]["status"] = "invalido"
    tasks[idx]["timestamp"] = str(datetime.datetime.now())

    return proxima(tasks, idx)


# ============================================================
# 5. REJEITAR + SUGESTÃO
# ============================================================
def sugerir(tasks, idx):

    texto = tasks[idx]["context"]
    sugestao = corrigir_requisito(texto)

    return f"Tarefa {idx+1}", texto, tasks[idx]["tipo"], tasks[idx]["subtipo"], sugestao, None, tasks, idx


# ============================================================
# 6. GUARDAR CORREÇÃO
# ============================================================
def guardar(tasks, idx, tipo, subtipo, corrigido):

    tasks[idx]["tipo"] = tipo
    tasks[idx]["subtipo"] = subtipo
    tasks[idx]["context_final"] = corrigido
    tasks[idx]["status"] = "corrigido"
    tasks[idx]["timestamp"] = str(datetime.datetime.now())

    return proxima(tasks, idx)


# ============================================================
# 7. PRÓXIMA
# ============================================================
def proxima(tasks, idx):

    idx += 1

    if idx >= len(tasks):
        df = pd.DataFrame(tasks)

        path = "resultado_validacao.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")

        return "✅ Finalizado", "", "", "", "", path, tasks, idx

    t = tasks[idx]

    return f"Tarefa {idx+1}/{len(tasks)}", t["context"], t["tipo"], t["subtipo"], "", None, tasks, idx


# ============================================================
# 8. UI
# ============================================================
with gr.Blocks() as demo:

    gr.Markdown("# ✅ Validação Humana")

    file = gr.File()
    btn_start = gr.Button("Iniciar")

    titulo = gr.Markdown()

    contexto = gr.Textbox(label="Requisito", lines=3)
    tipo = gr.Textbox(label="Classe (Tipo)")
    subtipo = gr.Textbox(label="Subclasse (Subtipo)")
    corrigido = gr.Textbox(label="Sugestão (LLM)", lines=3)

    with gr.Row():
        btn_aprovar = gr.Button("✅ Aprovar")
        btn_rejeitar = gr.Button("❌ Inválido")
        btn_sugerir = gr.Button("✏️ Sugerir")

    btn_guardar = gr.Button("💾 Guardar Correção")

    download = gr.File()
    state_tasks = gr.State([])
    state_idx = gr.State(0)

    btn_start.click(
        iniciar,
        inputs=file,
        outputs=[titulo, contexto, tipo, subtipo, corrigido, download, state_tasks, state_idx]
    )

    btn_aprovar.click(aprovar, inputs=[state_tasks, state_idx],
                      outputs=[titulo, contexto, tipo, subtipo, corrigido, download, state_tasks, state_idx])

    btn_rejeitar.click(rejeitar, inputs=[state_tasks, state_idx],
                       outputs=[titulo, contexto, tipo, subtipo, corrigido, download, state_tasks, state_idx])

    btn_sugerir.click(sugerir, inputs=[state_tasks, state_idx],
                      outputs=[titulo, contexto, tipo, subtipo, corrigido, download, state_tasks, state_idx])

    btn_guardar.click(guardar,
                      inputs=[state_tasks, state_idx, tipo, subtipo, corrigido],
                      outputs=[titulo, contexto, tipo, subtipo, corrigido, download, state_tasks, state_idx])

demo.launch(server_port=7860, share=True)