# =========================================================
# ✅ IMPORTS
# =========================================================
import os
import sys

import pandas as pd
import streamlit as st

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# 🔧 PATH FIX
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.cache import load_cache
from pipeline.extract import run_pipeline
from pipeline.loader import direto as load_raw_documents
from pipeline.merge import run_pipeline as merge_pipeline
from pipeline.classify import classificar
from myutils.metrics import mostrar_metricas


# =========================================================
# ✅ CONFIG
# =========================================================
st.set_page_config(layout="wide")
st.title("📋 Hybrid Software Requirements Preprocessing Datasets")


# =========================================================
# ✅ SESSION STATE
# =========================================================
if "cache" not in st.session_state:
    st.session_state.cache = load_cache()

if "ext" not in st.session_state:
    st.session_state.ext = None

if "cla" not in st.session_state:
    st.session_state.cla = None

if "final" not in st.session_state:
    st.session_state.final = None


# =========================================================
# ✅ DATASET (opcional referência)
# =========================================================
df_reference = pd.read_csv(
    "temp_uploads/software_requirements_extended.csv",
    encoding="utf-8",
    sep=",",
    on_bad_lines="skip"
)


# =========================================================
# ✅ LLM CONFIG
# =========================================================
st.sidebar.header("🤖 LLM Config")

modo = st.sidebar.radio("Modo", ["Local", "Cloud"])

client = None
model = None
provider = None


# =========================================================
# ✅ LOCAL
# =========================================================
if modo == "Local":

    provider = st.sidebar.selectbox("Provider", ["LM Studio", "Ollama"])

    if provider == "LM Studio":
        url = st.sidebar.text_input("URL", "http://localhost:1234/v1")

        try:
            tmp = OpenAI(base_url=url, api_key="lm")
            models = [m.id for m in tmp.models.list().data]
        except:
            models = ["llama-3", "mistral"]

        model = st.sidebar.selectbox("Modelo", models)
        client = OpenAI(base_url=url, api_key="lm")

    elif provider == "Ollama":
        model = st.sidebar.text_input("Modelo", value="llama3")


# =========================================================
# ✅ CLOUD
# =========================================================
elif modo == "Cloud":

    provider = st.sidebar.selectbox(
        "Provider",
        ["OpenAI", "Anthropic", "Gemini"]
    )

    api_key = st.sidebar.text_input("API Key", type="password")

    if provider == "OpenAI":
        model = st.sidebar.selectbox(
            "Modelo",
            ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "o3-mini"]
        )

    elif provider == "Anthropic":
        model = st.sidebar.selectbox(
            "Modelo",
            ["claude-3-opus", "claude-3.5-sonnet", "claude-3-sonnet"]
        )

    elif provider == "Gemini":
        model = st.sidebar.selectbox(
            "Modelo",
            ["gemini-1.5-pro", "gemini-1.5-flash"]
        )

    if api_key:
        if provider == "OpenAI":
            client = OpenAI(api_key=api_key)

        elif provider == "Anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

        elif provider == "Gemini":
            from google import genai
            client = genai.Client(api_key=api_key)


# =========================================================
# ✅ CONTEXTO
# =========================================================
ctx = {
    "client": client,
    "model": model,
    "provider": provider,
    "modo": modo,
    "cache": st.session_state.cache
}


# =========================================================
# ✅ UPLOAD
# =========================================================
files = st.file_uploader(
    "📂 Upload de ficheiros",
    accept_multiple_files=True,
    type=["txt", "csv", "xlsx", "xls", "pdf", "png", "jpg", "jpeg", "tiff", "tif"]
)

if files:
    st.success(f"✅ {len(files)} ficheiro(s) carregado(s)")


# =========================================================
# ✅ MENU
# =========================================================
menu = st.sidebar.selectbox(
    "Pipeline",
    ["Auto", "Extração", "Classificação", "Merge"]
)


# =========================================================
# 🔥 AUTO PIPELINE
# =========================================================
if menu == "Auto":

    if not files:
        st.info("📂 Upload to get started")

    elif st.button("🚀 RUN PIPELINE"):

        try:
            with st.spinner("🔄 Processing pipeline..."):

                df_extracted = run_pipeline(files, ctx)

                if df_extracted is None or not isinstance(df_extracted, pd.DataFrame):
                    st.error("❌ Pipeline inválido ou vazio")
                    st.stop()

                df_classified = classificar(df_extracted, ctx)

                st.session_state.ext = df_extracted
                st.session_state.cla = df_classified
                st.session_state.final = df_classified

                st.success(f"✅ Pipeline complete ({len(df_classified)})")

                st.dataframe(df_classified, use_container_width=True)
                mostrar_metricas(df_classified)

        except Exception as e:
            import traceback
            st.error("❌ Erro no pipeline")
            st.text(str(e))
            st.text(traceback.format_exc())


# =========================================================
# 🔥 EXTRAÇÃO
# =========================================================
elif menu == "Extração":

    if not files:
        st.warning("⚠️ Upload file")
        st.stop()

    if st.button("🚀 Extract"):

        try:
            with st.spinner("🔄 Extracting..."):

                df_extracted = run_pipeline(files, ctx)

                if df_extracted is None or not isinstance(df_extracted, pd.DataFrame):
                    st.error("❌ Extração inválida")
                    st.stop()

                st.session_state.ext = df_extracted
                st.session_state.final = df_extracted

                st.success(f"✅ {len(df_extracted)} Requirements extraídos")

                st.dataframe(df_extracted, use_container_width=True)
                mostrar_metricas(df_extracted)

        except Exception as e:
            import traceback
            st.error("❌ Extração falhou")
            st.text(str(e))
            st.text(traceback.format_exc())


# =========================================================
# 🔥 CLASSIFICAÇÃO
# =========================================================
elif menu == "Classificação":

    if not files and st.session_state.ext is None:
        st.warning("⚠️ Upload or run extraction first")
        st.stop()

    if st.button("🧠 Classify"):

        try:
            df_input = st.session_state.ext

            if df_input is None or not isinstance(df_input, pd.DataFrame):
                df_input = load_raw_documents(files)

            if df_input is None or df_input.empty:
                st.error("❌ Sem dados para classificar")
                st.stop()

            df_classified = classificar(df_input, ctx)

            st.session_state.cla = df_classified
            st.session_state.final = df_classified

            st.success("✅ Classificação concluída")

            st.dataframe(df_classified, use_container_width=True)
            mostrar_metricas(df_classified)

        except Exception as e:
            import traceback
            st.error("❌ Erro na classificação")
            st.text(str(e))
            st.text(traceback.format_exc())


# =========================================================
# 🔥 MERGE
# =========================================================
elif menu == "Merge":

    use_classified = st.session_state.cla is not None

    if not files and not use_classified:
        st.error("❌ Upload ou classificação necessária")
        st.stop()

    if st.button("🔀 Executar Merge"):

        try:
            with st.spinner("🔄 Merge..."):

                if use_classified:
                    df_final = st.session_state.cla.copy()
                else:
                    df_final = merge_pipeline(files)

                if df_final is None or not isinstance(df_final, pd.DataFrame):
                    st.error("❌ Merge inválido")
                    st.stop()

                st.session_state.final = df_final

                st.success(f"✅ Merge concluído ({len(df_final)})")

                st.dataframe(df_final, use_container_width=True)
                mostrar_metricas(df_final)

                st.download_button(
                    "📥 Download CSV",
                    df_final.to_csv(index=False).encode("utf-8"),
                    "final.csv"
                )

        except Exception as e:
            import traceback
            st.error("❌ Erro no merge")
            st.text(str(e))
            st.text(traceback.format_exc())