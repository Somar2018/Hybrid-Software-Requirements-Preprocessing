import streamlit as st
import pandas as pd
from pathlib import Path
from typing import List, Dict
from myutils.i18n import t, translations
import myutils.i18n as i18n

# =========================
# STATE
# =========================
if "tasks" not in st.session_state:
    st.session_state.tasks: List[Dict] = []
    st.session_state.idx = 0
    st.session_state.suggest_mode = False


# =========================
# START
# =========================
def iniciar(file):
    try:
        df = pd.read_csv(file)
    except:
        df = pd.read_excel(file)

    df.columns = df.columns.str.lower().str.strip()

    def find_col(cols, keywords):
        return next((c for c in cols if any(k in c for k in keywords)), None)

    col_text = find_col(df.columns, ("text", "requirement", "requisito"))
    col_class = find_col(df.columns, ("class", "classe"))
    col_sub = find_col(df.columns, ("sub", "subclass"))

    df["context"] = df[col_text].astype(str)
    df["type"] = df[col_class].astype(str) if col_class else ""
    df["subtype"] = df[col_sub].astype(str) if col_sub else ""

    st.session_state.tasks = df.to_dict("records")
    st.session_state.idx = 0


# =========================
# GET TASK
# =========================
def get_task():
    if st.session_state.idx >= len(st.session_state.tasks):
        return None
    return st.session_state.tasks[st.session_state.idx]


# =========================
# NEXT
# =========================
def proxima():
    st.session_state.idx += 1
    st.session_state.suggest_mode = False


# =========================
# APPROVE
# =========================
def aprovar(tipo, subtipo, corrigido):
    tsk = get_task()

    tsk["original_type"] = tsk.get("type")
    tsk["original_subtype"] = tsk.get("subtype")

    tsk["type"] = tipo
    tsk["subtype"] = subtipo
    tsk["context_final"] = corrigido
    tsk["classification_status"] = "approved"

    proxima()


# =========================
# REJECT
# =========================
def rejeitar():
    tsk = get_task()
    tsk["classification_status"] = "rejected"
    proxima()


# =========================
# SUGGEST MODE
# =========================
def ativar_sugestao():
    st.session_state.suggest_mode = True


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
    tsk = get_task()
    tsk["context_final"] = corrigido
    tsk["classification_status"] = "suggested"
    proxima()


# =========================
# FINAL
# =========================
def finalizar():
    df = pd.DataFrame(st.session_state.tasks)
    path = Path("final_result.csv")
    df.to_csv(path, index=False)
    return path


# =========================
# UI
# =========================
st.title(f"✅ {t('structural_validation')}")

# LANGUAGE
lang = st.selectbox("Language", list(translations.keys()), index=list(translations.keys()).index(i18n.LANG))
i18n.LANG = lang

# FILE
file = st.file_uploader(t("start"), type=["csv", "xlsx"])

if file:
    iniciar(file)

task = get_task()

# =========================
# PROCESSING SCREEN
# =========================
if task:

    st.subheader(f"{t('phase_title')} ({st.session_state.idx+1}/{len(st.session_state.tasks)})")

    contexto = st.text_area(t("requirement"), value=task.get("context", ""))

    tipo = st.selectbox(
        t("class"),
        ["FR", "NFR", "Other"],
        index=0
    )

    subtipo = st.selectbox(
        t("subclass"),
        [
            "Functional",
            "Performance",
            "Security",
            "Usability",
            "Reliability",
            "Other",
            "Unknown"
        ],
    )

    corrigido = st.text_area(
        t("correction"),
        value=task.get("context_final", "")
    )

    # BOTÕES
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(f"✅ {t('approve')}"):
            aprovar(tipo, subtipo, corrigido)
            st.rerun()

    with col2:
        if st.button(f"❌ {t('reject')}"):
            rejeitar()
            st.rerun()

    with col3:
        if st.button(f"✏️ {t('suggest')}"):
            sugestao = sugerir(contexto)
            st.session_state["suggested_text"] = sugestao
            ativar_sugestao()

    # MODO SUGESTÃO
    if st.session_state.suggest_mode:
        corrigido = st.text_area(
            t("correction"),
            value=st.session_state.get("suggested_text", "")
        )

        if st.button(f"💾 {t('save_suggestion')}"):
            guardar_sugestao(corrigido)
            st.rerun()

# =========================
# FINAL SCREEN
# =========================
else:
    if len(st.session_state.tasks) > 0:
        st.success(t("completed"))

        file_path = finalizar()

        with open(file_path, "rb") as f:
            st.download_button(
                label=t("download"),
                data=f,
                file_name="final_result.csv",
                mime="text/csv"
            )

    else:
        st.info(t("no_file"))
# =========================
# RUN
# =========================
