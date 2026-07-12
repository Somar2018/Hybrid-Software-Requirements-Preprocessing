# =========================================================
# ✅ IMPORTS
# =========================================================
import os
import sys
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from core.cache import get_cache_path, load_cache, save_cache
from pipeline.clean import run_pipeline as run_cleaning


# =========================================================
# ✅ LOAD ENV
# =========================================================
load_dotenv()

USER = os.getenv("APP_USER", "admin")
PASS = os.getenv("APP_PASS", "nlp4srv_2026")


# =========================================================
# ✅ SESSION STATE (ANTES DO LOGIN ✅)
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "cache" not in st.session_state:
    st.session_state.cache = load_cache()

if "ext" not in st.session_state:
    st.session_state.ext = None

if "cla" not in st.session_state:
    st.session_state.cla = None

if "final" not in st.session_state:
    st.session_state.final = None


# =========================================================
# ✅ LOGIN FUNCTION
# =========================================================
def login():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Entrar"):
        if username == USER and password == PASS:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("❌ Credenciais inválidas")


# 🔴 BLOQUEIO
if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================================
# ✅ IMPORTS RESTANTES (depois do login)
# =========================================================
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# 🔧 PATH FIX
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pipeline.extract
import pipeline.loader
import pipeline.merge
import pipeline.classify
import myutils.metrics

import pathlib


# =========================================================
# ✅ CONFIG
# =========================================================
st.set_page_config(layout="wide")
st.title("📋 Hybrid Software Requirements Preprocessing Datasets")

# ✅ LOGOUT
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

def get_project_name(file):
    """
    Detecta automaticamente o nome do projeto.
    Primeiro tenta pelo nome do ficheiro.
    Depois tenta pelo conteúdo da coluna 'text'.
    """

    filename = pathlib.Path(file.name).stem.lower()

    # Regras pelo nome do ficheiro
    mappings = {
        "cps": "Card Payment System",
        "epurse": "Electronic Purse System",
        "e_purse": "Electronic Purse System",
        "epu": "Electronic Purse System",
    }

    for key, value in mappings.items():
        if key in filename:
            return value

    # Regras pelo conteúdo
    try:
        file.seek(0)
        df = pd.read_csv(file)

        if "text" in df.columns:

            text = " ".join(
                df["text"].astype(str).head(100)
            ).lower()

            if any(x in text for x in
                ["merchant", "issuer", "acquirer", "payment"]):
                return "Card Payment System"

            if any(x in text for x in
                ["electronic purse", "wallet", "smart card"]):
                return "Electronic Purse System"

            if any(x in text for x in
                ["library", "book", "borrower"]):
                return "Library Management System"

            if any(x in text for x in
                ["patient", "hospital", "doctor"]):
                return "Hospital Management System"

    except Exception:
        pass

    # fallback
    return (
        pathlib.Path(file.name)
        .stem
        .replace("_", " ")
        .replace("-", " ")
        .title()
    )

def enrich_with_metadata(df):

    if df is None:
        return df

    if not isinstance(df, pd.DataFrame):
        return df

    if df.empty:
        return df

    if "file_index" not in df.columns:
        st.warning(
            "⚠️ file_index não encontrado no dataframe"
        )
        return df

    metadata_df = st.session_state.get(
        "project_metadata",
        pd.DataFrame()
    )

    if metadata_df.empty:
        st.warning(
            "⚠️ project_metadata vazio"
        )
        return df

    metadata_map = {
        int(row["file_index"]): {
            "project_id": row["Project ID"],
            "project_name": row["Project Name"],
            "dataset_id": row["Dataset ID"]
        }
        for _, row in metadata_df.iterrows()
    }

    df = df.copy()

    df["file_index"] = pd.to_numeric(
        df["file_index"],
        errors="coerce"
    )

    df["project_id"] = df["file_index"].map(
        lambda x: metadata_map.get(
            int(x),
            {}
        ).get(
            "project_id",
            ""
        )
        if pd.notna(x)
        else ""
    )

    df["project_name"] = df["file_index"].map(
        lambda x: metadata_map.get(
            int(x),
            {}
        ).get(
            "project_name",
            ""
        )
        if pd.notna(x)
        else ""
    )

    df["dataset_id"] = df["file_index"].map(
        lambda x: metadata_map.get(
            int(x),
            {}
        ).get(
            "dataset_id",
            ""
        )
        if pd.notna(x)
        else ""
    )

    return df


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

        if OpenAI:
            try:
                tmp = OpenAI(base_url=url, api_key="lm")
                models = [m.id for m in tmp.models.list().data]
            except Exception:
                models = ["llama-3", "mistral"]

            model = st.sidebar.selectbox("Model", models)
            try:
                client = OpenAI(
                    base_url=url,
                    api_key="lm"
                )
            except Exception:
                client = None
        else:
            models = ["llama-3", "mistral"]
            model = st.sidebar.selectbox("Model", models)
            st.error(
                "OpenAI package not installed"
            )

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
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
            except Exception:
                client = None

        elif provider == "Gemini":
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
            except Exception:
                client = None


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
    type=[
        "txt", "csv", "xlsx", "xls",
        "pdf", "png", "jpg", "jpeg",
        "tiff", "tif"
    ]
)

metadata_map = {}

if files:

    st.success(f"✅ {len(files)} file(s) uploaded")

    metadata = []

    for i, file in enumerate(files, start=1):

        metadata.append({
            "Project ID": f"P{i:03d}",
            "Project Name": get_project_name(file),
            "Dataset ID": f"DS{i:03d}",
            "File Name": file.name
        })

    metadata_df = pd.DataFrame(metadata)

    metadata_map = {
        row["File Name"]: {
            "project_id": row["Project ID"],
            "project_name": row["Project Name"],
            "dataset_id": row["Dataset ID"]
        }
        for _, row in metadata_df.iterrows()
    }

    st.session_state.project_metadata = metadata_df
    st.session_state.metadata_map = metadata_map

# =========================================================
# ✅ MENU
# =========================================================
menu = st.sidebar.selectbox(
    "Pipeline",
    ["Auto", "Extraction", "Cleaning","Classification", "Merge"]
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

                df_extracted = pipeline.extract.run_pipeline(files, ctx)

                df_extracted = enrich_with_metadata(
                    df_extracted
                )

                if (
                    df_extracted is None
                    or not isinstance(df_extracted, pd.DataFrame)
                ):
                    st.error("❌ Invalid or empty pipeline")
                    st.stop()

                df_classified = pipeline.classify.classificar(
                    df_extracted,
                    ctx
                )

                df_classified = enrich_with_metadata(
                    df_classified
                )

                st.session_state.ext = df_extracted
                st.session_state.cla = df_classified
                st.session_state.final = df_classified

                st.success(
                    f"✅ Pipeline complete ({len(df_classified)})"
                )

                st.dataframe(
                    df_classified,
                    width="stretch"
                )

                myutils.metrics.mostrar_metricas(df_classified)

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

                df_extracted = pipeline.extract.run_pipeline(files, ctx)
                df_extracted = enrich_with_metadata(df_extracted)

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

elif menu == "Cleaning":

    if not files:
        st.warning("⚠️ Upload file first")
        st.stop()

    if st.button("🧹 Run Cleaning"):

        try:

            with st.spinner("🧹 Cleaning dataset..."):

                df_clean = run_cleaning(files)

                if df_clean is None:
                    st.error("❌ Cleaning returned None")
                    st.stop()

                if not isinstance(df_clean, pd.DataFrame):
                    st.error("❌ Invalid cleaning output")
                    st.stop()

                if df_clean.empty:
                    st.warning("⚠️ No records found after cleaning")
                    st.stop()

                # guardar na sessão
                st.session_state.clean = df_clean
                st.session_state.final = df_clean

                st.success(
                    f"✅ Cleaning completed ({len(df_clean)} rows × {len(df_clean.columns)} columns)"
                )

                # métricas rápidas
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Rows", len(df_clean))

                with col2:
                    st.metric("Columns", len(df_clean.columns))

                with col3:
                    st.metric(
                        "Missing Values",
                        int(df_clean.isna().sum().sum())
                    )

                st.subheader("🧹 Clean Dataset")

                st.dataframe(
                    df_clean,
                    width="stretch"
                )

                csv = (
                    df_clean
                    .to_csv(
                        index=False,
                        encoding="utf-8"
                    )
                    .encode("utf-8")
                )

                st.download_button(
                    label="📥 Download Clean CSV",
                    data=csv,
                    file_name="clean_dataset.csv",
                    mime="text/csv"
                )

        except Exception as e:

            import traceback

            st.error("❌ Cleaning failed")

            st.code(
                traceback.format_exc(),
                language="python"
            )

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
                df_input = pipeline.loader.direto(files)

            if df_input is None or df_input.empty:
                st.error("❌ No data to classify")
                st.stop()

            df_classified = pipeline.classify.classificar(df_input, ctx)

            df_classified = enrich_with_metadata(
                df_classified
            )

            # ✅ guardar corretamente
            st.session_state.cla = df_classified
            st.session_state.final = df_classified

            st.success("✅ Classification completed")

            st.dataframe(df_classified, width="stretch")
            myutils.metrics.mostrar_metricas(df_classified)

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
                    df_final = pipeline.merge.run_pipeline(files)

                if df_final is None or not isinstance(df_final, pd.DataFrame):
                    st.error("❌ Invalid merge")
                    st.stop()

                # =====================================================
                # ENRIQUECER COM METADATA
                # =====================================================
                metadata_map = st.session_state.get(
                    "metadata_map",
                    {}
                )

                if "source_file" in df_final.columns:
                    df_final["project_id"] = (
                        df_final["source_file"]
                        .map(
                            lambda x: metadata_map.get(
                                x,
                                {}
                            ).get(
                                "project_id",
                                ""
                            )
                        )
                    )

                    df_final["project_name"] = (
                        df_final["source_file"]
                        .map(
                            lambda x: metadata_map.get(
                                x,
                                {}
                            ).get(
                                "project_name",
                                ""
                            )
                        )
                    )

                    df_final["dataset_id"] = (
                        df_final["source_file"]
                        .map(
                            lambda x: metadata_map.get(
                                x,
                                {}
                            ).get(
                                "dataset_id",
                                ""
                            )
                        )
                    )

                st.session_state.final = df_final

                metadata_df = st.session_state.get(
                    "project_metadata",
                    pd.DataFrame()
                )

                if not metadata_df.empty and "project_id" in df_final.columns:
                    project_name_map = {
                        row["Project ID"]: row["Project Name"]
                        for _, row in metadata_df.iterrows()
                    }
                    df_final["project_name"] = (
                        df_final["project_id"]
                        .map(project_name_map)
                        .fillna(df_final.get("project_name", ""))
                    )

                st.success(
                    f"✅ Merge completed ({len(df_final)})"
                )

                df_display = pd.DataFrame()

                df_display["Requirement ID"] = (
                    df_final["id"]
                    if "id" in df_final.columns
                    else [
                        f"REQ_{i:05d}"
                        for i in range(
                            1,
                            len(df_final) + 1
                        )
                    ]
                )

                df_display["Project ID"] = (
                    df_final["project_id"]
                    if "project_id" in df_final.columns
                    else ""
                )

                df_display["Project Name"] = (
                    df_final["project_name"]
                    if "project_name" in df_final.columns
                    else ""
                )

                df_display["Dataset ID"] = (
                    df_final["dataset_id"]
                    if "dataset_id" in df_final.columns
                    else ""
                )

                if "requirement_text" in df_final.columns:
                    df_display["Requirement Text"] = (
                        df_final["requirement_text"]
                    )
                elif "text" in df_final.columns:
                    df_display["Requirement Text"] = (
                        df_final["text"]
                    )
                else:
                    df_display["Requirement Text"] = ""

                df_display["class"] = (
                    df_final["class"]
                    if "class" in df_final.columns
                    else ""
                )

                df_display["subclass"] = (
                    df_final["subclass"]
                    if "subclass" in df_final.columns
                    else ""
                )

                df_display["confidence"] = (
                    df_final["confidence"]
                    if "confidence" in df_final.columns
                    else 0.0
                )

                st.dataframe(
                    df_display,
                    width="stretch"
                )

                st.download_button(
                    "📥 Download CSV",
                    df_display
                    .to_csv(index=False)
                    .encode("utf-8"),
                    "final.csv",
                    "text/csv"
                )

        except Exception as e:
            import traceback

            st.error("❌ Merge error")
            st.text(str(e))
            st.text(traceback.format_exc())

            if "df_final" in locals():
                st.write("DEBUG - COLUNAS")
                st.write(df_final.columns.tolist())

# =========================================================
# ✅ RLHF - HUMAN REVIEW
# =========================================================

df = pd.DataFrame()

st.subheader("🔁 Human Review Requirements (RLHF)")

if st.session_state.final is None:
    st.info("⚠️ Run Extraction/Classify first.")

else:

    df = st.session_state.final.copy()

    # Garantir colunas necessárias
    if "confidence" not in df.columns:
        df["confidence"] = 0.0

    if "class" not in df.columns:
        df["class"] = "Unknown"

    if "subclass" not in df.columns:
        df["subclass"] = "Unknown"

    if "id" not in df.columns:
        if "global_id" in df.columns:
            df["id"] = df["global_id"]
        else:
            df["id"] = [
                f"F0_REQ_{i:05d}"
                for i in range(1, len(df) + 1)
            ]

    def needs_human_review(row):
        reasons = []

        try:
            conf = float(row.get("confidence", 0))
        except Exception:
            conf = 0

        if conf < 0.50:
            reasons.append("low_confidence")

        if row.get("class", "") in ["Unknown", "", None]:
            reasons.append("unknown_class")

        if row.get("subclass", "") in ["Unknown", "", None]:
            reasons.append("unknown_subclass")

        return (
            len(reasons) > 0,
            ";".join(reasons)
        )

try:
    # streamlit >=1.22 has link_button
    st.link_button("🤖 Human in-the-Loop (RLHF)", "http://localhost:7861")
except Exception:
    st.markdown("[🤖 Human in-the-Loop (RLHF)](http://localhost:7861)")

import logging

logger = logging.getLogger(__name__)
logger.info(df.columns.tolist())

# =========================================================
# 🔗 HUMAN IN THE LOOP
# =========================================================

df = st.session_state.get("cla", None)

if df is not None:

    if "confidence" not in df.columns:
        df["confidence"] = 0.0

    low_conf = df[df["confidence"] < 0.5]

    medium_conf = df[
        (df["confidence"] >= 0.5)
        & (df["confidence"] < 0.8)
    ]

    high_conf = df[df["confidence"] >= 0.8]

    st.write(
        f"📌 Total High Confidence Requirements (0.8 - 1.0): {len(high_conf)}"
    )
    st.subheader("✅ High Confidence")
    st.dataframe(high_conf, width="stretch")

    st.write(
        f"📌 Total Medium Confidence Requirements (0.5 - 0.8): {len(medium_conf)}"
    )
    st.subheader("🟡 Medium Confidence")
    st.dataframe(medium_conf, width="stretch")

    st.write(
        f"📌 Total Low Confidence Requirements (< 0.5): {len(low_conf)}"
    )
    st.subheader("🔴 Low Confidence")
    st.dataframe(low_conf, width="stretch")

else:
    st.warning("⚠️ Please run classification first")