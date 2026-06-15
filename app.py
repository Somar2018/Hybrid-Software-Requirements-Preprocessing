# =========================================================
# ✅ IMPORTS
# =========================================================
import os
import sys

import pandas as pd
import streamlit as st

import pandas as pd
import datetime

from collections import Counter
import random

if "rlhf_cases" not in st.session_state:
    st.session_state.rlhf_cases = []

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# 🔧 PATH FIX
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if "pipeline" in sys.modules:
    del sys.modules["pipeline"]

from core.cache import load_cache
from pipeline.extract import run_pipeline
from pipeline.loader import direto as load_raw_documents
from pipeline.merge import run_pipeline as merge_pipeline
from pipeline.classify import classificar, detect_free_subclass
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
# ✅ DATASET (optional reference)
# =========================================================
try:
    df_reference = pd.read_csv(
        "temp_uploads/software_requirements_extended.csv",
        encoding="utf-8",
        sep=",",
        on_bad_lines="skip"
    )
except:
    df_reference = pd.DataFrame()

# =========================================================
# ✅ LLM CONFIG
# =========================================================
st.sidebar.header("🤖 LLM Configuration")

modo = st.sidebar.radio("Mode", ["Local", "Cloud"])

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

        model = st.sidebar.selectbox("Model", models)
        client = OpenAI(base_url=url, api_key="lm")

    elif provider == "Ollama":
        model = st.sidebar.text_input("Model", value="llama3")


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
            "Model",
            ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "o3-mini"]
        )

    elif provider == "Anthropic":
        model = st.sidebar.selectbox(
            "Model",
            ["claude-3-opus", "claude-3.5-sonnet", "claude-3-sonnet"]
        )

    elif provider == "Gemini":
        model = st.sidebar.selectbox(
            "Model",
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
# ✅ CONTEXT
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
    "📂 Upload files",
    accept_multiple_files=True,
    type=["txt", "csv", "xlsx", "xls", "pdf", "png", "jpg", "jpeg", "tiff", "tif"]
)

if files:
    st.success(f"✅ {len(files)} file(s) uploaded")


# =========================================================
# ✅ MENU
# =========================================================
menu = st.sidebar.selectbox(
    "Pipeline",
    ["Auto", "Extraction", "Classification", "Merge"]
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
                    st.error("❌ Invalid or empty pipeline")
                    st.stop()

                df_classified = classificar(df_extracted, ctx)

                st.session_state.ext = df_extracted
                st.session_state.cla = df_classified
                st.session_state.final = df_classified

                st.success(f"✅ Pipeline complete ({len(df_classified)})")

                st.dataframe(df_classified, width="stretch")
                mostrar_metricas(df_classified)

        except Exception as e:
            import traceback
            st.error("❌ Pipeline error")
            st.text(str(e))
            st.text(traceback.format_exc())


# =========================================================
# 🔥 EXTRACTION
# =========================================================
elif menu == "Extraction":

    if not files:
        st.warning("⚠️ Upload file")
        st.stop()

    if st.button("🚀 Extract"):

        try:
            with st.spinner("🔄 Extracting..."):

                df_extracted = run_pipeline(files, ctx)

                if df_extracted is None or not isinstance(df_extracted, pd.DataFrame):
                    st.error("❌ Invalid extraction")
                    st.stop()

                st.session_state.ext = df_extracted
                st.session_state.final = df_extracted

                st.success(f"✅ {len(df_extracted)} Requirements extracted")

                st.dataframe(df_extracted, width="stretch")

        except Exception as e:
            import traceback
            st.error("❌ Extraction failed")
            st.text(str(e))
            st.text(traceback.format_exc())


# =========================================================
# 🔥 CLASSIFICATION
# =========================================================
elif menu == "Classification":

    if not files and st.session_state.ext is None:
        st.warning("⚠️ Upload or run extraction first")
        st.stop()

    # ✅ inicialização segura
    if "cla" not in st.session_state:
        st.session_state.cla = None

    if st.button("🧠 Classify"):

        try:
            df_input = st.session_state.ext

            if df_input is None or not isinstance(df_input, pd.DataFrame):
                df_input = load_raw_documents(files)

            if df_input is None or df_input.empty:
                st.error("❌ No data to classify")
                st.stop()

            df_classified = classificar(df_input, ctx)

            # ✅ guardar corretamente
            st.session_state.cla = df_classified
            st.session_state.final = df_classified

            st.success("✅ Classification completed")

            st.dataframe(df_classified, width="stretch")
            mostrar_metricas(df_classified)

        except Exception as e:
            import traceback
            st.error("❌ Classification error")
            st.text(str(e))
            st.text(traceback.format_exc())

# =========================================================
# 🔥 MERGE
# =========================================================
elif menu == "Merge":

    use_classified = st.session_state.cla is not None

    if not files and not use_classified:
        st.error("❌ Upload or classification required")
        st.stop()

    if st.button("🔀 Run Merge"):

        try:
            with st.spinner("🔄 Merging..."):

                if use_classified:
                    df_final = st.session_state.cla.copy()
                else:
                    df_final = merge_pipeline(files)

                if df_final is None or not isinstance(df_final, pd.DataFrame):
                    st.error("❌ Invalid merge")
                    st.stop()

                st.session_state.final = df_final

                st.success(f"✅ Merge completed ({len(df_final)})")

                st.dataframe(df_final, width="stretch")
                mostrar_metricas(df_final)

                st.download_button(
                    "📥 Download CSV",
                    df_final.to_csv(index=False).encode("utf-8"),
                    "final.csv"
                )

        except Exception as e:
            import traceback
            st.error("❌ Merge error")
            st.text(str(e))
            st.text(traceback.format_exc())

# =========================================================
# ✅ RLHF - HUMAN REVIEW (CORRETO)
# =========================================================

st.subheader("🔁 Human Review Requirements (RLHF)")

if st.session_state.final is None:
    st.info("⚠️ Run Extraction/Classify first.")
else:

    df = st.session_state.final.copy()

    #st.write("📊 Confidence Distribution")
    #st.write(df["confidence"].describe())

    def needs_human_review(row):
        reasons = []

        texto = str(row["text"]).lower()
        sub = str(row["subclass"])
        cls = str(row["class"])
        conf = float(row["confidence",0])

        # ✅ CONFIDENCE (ajustado ao teu dataset)
        if conf < 0.49:
            reasons.append("low_confidence")

        # ✅ regras adicionais
        if len(texto) > 300:
            reasons.append("too_long")

        if len(texto) < 20:
            reasons.append("too_short")

        flagged = len(reasons) > 0
        return flagged, ", ".join(reasons)

    rlhf_cases = []

    for _, row in df.iterrows():
        flagged, reasons = needs_human_review(row)

        if flagged:
            rlhf_cases.append({
                "id": row["id"],
                "text": row["text"],
                "class": row["class"],
                "subclass": row["subclass"],
                "confidence": row["confidence"],
                "reasons_rlhf": reasons,
                "correct_class": "",
                "correct_subclass": "",
                "comment": ""
            })

    df_rlhf = pd.DataFrame(rlhf_cases)

    st.write(f"📌 Total for review: {len(df_rlhf)}")

    if not df_rlhf.empty:
        df_rlhf = df_rlhf.sort_values("confidence")
        st.dataframe(df_rlhf, width="stretch")
    else:
        st.success("✅ No cases require review (confidence too high)")

# =========================
# 4. GERAR RLHF LIST
# =========================
df_rlhf = pd.DataFrame()
df = None
if df is not None:
    rlhf_cases = []

    for _, row in df.iterrows():
        flagged, reasons = needs_human_review(row)

        if flagged:
            rlhf_cases.append({
                "id": row["id"],
                "text": row["text"],
                "class": row["class"],
                "subclass": row["subclass"],
                "confidence": row["confidence"],
                "reasons_rlhf": reasons,
                "correct_class": "",
                "correct_subclass": "",
                "comment": ""
            })

st.link_button("Human in-the-Loop (RLHF)", "http://localhost:7861")
# =========================================================
# 🔗 HUMAN IN THE LOOP
# =========================================================

df = st.session_state.get("cla", None)

if df is not None:

    # 🔴 Baixa confiança
    low_conf = df[df["confidence"] < 0.5]

    # 🟡 Média confiança
    medium_conf = df[
        (df["confidence"] >= 0.5) & (df["confidence"] < 0.8)
    ]

    # ✅ Alta confiança
    high_conf = df[df["confidence"] >= 0.8]

    # Mostrar no Streamlit
    st.write(f"📌 Total High Confidence Requirements (0.8 - 1.0): {len(high_conf)}")
    st.subheader("✅ High Confidence")
    st.dataframe(high_conf)

    st.write(f"📌 Total Medium Confidence Requirements (0.5 - 0.7): {len(medium_conf)}")
    st.subheader("🟡 Medium Confidence")
    st.dataframe(medium_conf)

else:
    st.warning("⚠️ Please run the classification first")