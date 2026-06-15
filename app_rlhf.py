import gradio as gr
import pandas as pd
from pathlib import Path
from typing import List, Dict
from myutils.i18n import t, translations
import myutils.i18n as i18n   # necessário para alterar LANG dinamicamente


tasks: List[Dict] = []
idx: int = 0


# =========================
# START
# =========================
def iniciar(file):
    global tasks, idx

    if file is None:
        return (t("no_file"), "", "", "", "", None,
                gr.update(), gr.update(), gr.update())

    try:
        df = pd.read_csv(file.name)
    except:
        df = pd.read_excel(file.name)

    df.columns = df.columns.str.lower().str.strip()

    def find_col(cols, keywords):
        return next((c for c in cols if any(k in c for k in keywords)), None)

    col_text = find_col(df.columns, ("text", "requirement", "requisito"))
    col_class = find_col(df.columns, ("class", "classe"))
    col_sub = find_col(df.columns, ("sub", "subclass"))

    df["context"] = df[col_text].astype(str)
    df["type"] = df[col_class].astype(str) if col_class else ""
    df["subtype"] = df[col_sub].astype(str) if col_sub else ""

    tasks = df.to_dict("records")
    idx = 0

    return atualizar()


# =========================
# UPDATE
# =========================
def atualizar():
    global tasks, idx

    if idx >= len(tasks):
        return finalizar()

    tsk = tasks[idx]

    return (
        f"{t('phase_title')} ({idx+1}/{len(tasks)})",
        tsk.get("context", ""),
        tsk.get("type", ""),
        tsk.get("subtype", ""),
        tsk.get("context_final", ""),
        None,
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(visible=False),
    )


# =========================
# NEXT
# =========================
def proxima():
    global idx
    idx += 1
    return atualizar()


# =========================
# APPROVE
# =========================
def aprovar(tipo, subtipo, corrigido):
    global tasks, idx

    tsk = tasks[idx]

    tsk["original_type"] = tsk.get("type")
    tsk["original_subtype"] = tsk.get("subtype")

    tsk["type"] = tipo
    tsk["subtype"] = subtipo
    tsk["context_final"] = corrigido
    tsk["classification_status"] = "approved"

    return proxima()


# =========================
# REJECT
# =========================
def rejeitar():
    global tasks, idx
    tasks[idx]["classification_status"] = "rejected"
    return proxima()


# =========================
# ENABLE SUGGESTION MODE
# =========================
def ativar_sugestao():
    return (
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(visible=True),
    )


# =========================
# AUTO-SUGGEST
# =========================
def sugerir(texto):
    if not texto:
        return ""
    texto = texto.strip()
    if not texto[0].isupper():
        texto = texto[0].upper() + texto[1:]
    return "The system shall " + texto


# =========================
# SAVE SUGGESTION
# =========================
def guardar_sugestao(corrigido):
    global tasks, idx

    tasks[idx]["context_final"] = corrigido
    tasks[idx]["classification_status"] = "suggested"

    return proxima()


# =========================
# FINAL
# =========================
def finalizar():
    df = pd.DataFrame(tasks)
    path = Path.cwd() / "final_result.csv"
    df.to_csv(path, index=False)

    return (
        t("completed"),
        "", "", "", "",
        str(path),
        gr.update(),
        gr.update(),
        gr.update(),
    )


# =========================
# UI
# =========================
with gr.Blocks() as demo:

    # LANGUAGE SELECTOR
    with gr.Row():
        lang_selector = gr.Dropdown(
            label="Language",
            choices=list(translations.keys()),
            value=i18n.LANG
        )

    def change_lang(lang):
        i18n.LANG = lang
        return gr.update()

    lang_selector.change(change_lang, lang_selector, None)

    # TITLE
    gr.Markdown(f"# ✅ {t('structural_validation')}")

    file = gr.File()
    btn_start = gr.Button(t("start"))

    titulo = gr.Markdown()
    contexto = gr.Textbox(label=t("requirement"))

    tipo = gr.Dropdown(
        label=t("class"),
        choices=["FR", "NFR", "Other"],
        allow_custom_value=True
    )

    subtipo = gr.Dropdown(
        label=t("subclass"),
        choices=[
            "Functional",
            "Performance",
            "Security",
            "Usability",
            "Reliability",
            "Other",
            "Unknown"
        ],
        allow_custom_value=True
    )

    corrigido = gr.Textbox(label=t("correction"))

    btn_aprovar = gr.Button(f"✅ {t('approve')}")
    btn_rejeitar = gr.Button(f"❌ {t('reject')}")
    btn_sugerir = gr.Button(f"✏️ {t('suggest')}")
    btn_guardar = gr.Button(f"💾 {t('save_suggestion')}", visible=False)

    download = gr.File(label=t("download"))

    outputs = [
        titulo, contexto,
        tipo, subtipo,
        corrigido,
        download,
        btn_aprovar,
        btn_rejeitar,
        btn_guardar
    ]

    # START
    btn_start.click(iniciar, file, outputs)

    # APPROVE
    btn_aprovar.click(
        aprovar,
        [tipo, subtipo, corrigido],
        outputs
    )

    # REJECT
    btn_rejeitar.click(
        rejeitar,
        None,
        outputs
    )

    # SUGGEST TEXT
    btn_sugerir.click(
        sugerir,
        contexto,
        corrigido
    )

    # ENABLE SUGGESTION MODE
    btn_sugerir.click(
        ativar_sugestao,
        None,
        [btn_aprovar, btn_rejeitar, btn_guardar]
    )

    # SAVE
    btn_guardar.click(
        guardar_sugestao,
        corrigido,
        outputs
    )
# =========================
# RUN
# =========================
if __name__ == "__main__":
    demo.launch(server_port=7861)
