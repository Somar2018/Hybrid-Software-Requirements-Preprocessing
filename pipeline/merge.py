# =========================================================
# pipeline/merge.py - Robust file merge pipeline
# =========================================================

import logging
from typing import Any, Iterable, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

FileLike = Union[str, Any]
TEXT_COLUMN_ALIASES = {
    "text": "text",
    "requirement_text": "text",
    "requirement text": "text",
    "description": "text",
}

# =========================================================
# ✅ LEITURA AUTOMÁTICA (CSV + EXCEL)
# =========================================================
def read_uploaded_file(f: FileLike) -> Optional[pd.DataFrame]:
    """Read Streamlit uploaded files or file-like objects into a DataFrame."""
    try:
        name = getattr(f, "name", str(f)).lower()
        if name.endswith(".csv"):
            return pd.read_csv(f, sep=None, engine="python")
        if name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(f)

        logger.warning("Unsupported upload format: %s", name)
        return None
    except Exception as exc:
        logger.error("Failed to read uploaded file %s: %s", getattr(f, 'name', str(f)), exc)
        return None


# =========================================================
# ✅ UNIFICAR DATASETS
# =========================================================
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def _find_text_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if col in TEXT_COLUMN_ALIASES:
            return TEXT_COLUMN_ALIASES[col]
        if "text" in col:
            return col
    return None


def unify_files(dfs: Iterable[pd.DataFrame]) -> pd.DataFrame:
    clean_dfs: List[pd.DataFrame] = []

    for idx, df in enumerate(dfs):
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            continue

        df = _normalize_columns(df)
        text_col = _find_text_column(df)

        if text_col is None:
            df["text"] = ""
        elif text_col != "text":
            df.rename(columns={text_col: "text"}, inplace=True)

        if "text" not in df.columns:
            df["text"] = ""

        df["text"] = df["text"].astype(str).str.strip()

        if df.empty:
            continue

        df["global_id"] = [f"F{idx}_REQ_{i:05d}" for i in range(len(df))]
        df["source"] = f"file_{idx}"
        clean_dfs.append(df)

    if not clean_dfs:
        return pd.DataFrame(columns=["global_id", "text", "type", "subclass", "source"])

    return pd.concat(clean_dfs, ignore_index=True)


# =========================================================
# ✅ FINALIZAÇÃO
# =========================================================
def finalize_dataset(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame({
            "global_id": [],
            "text": [],
            "type": [],
            "subclass": [],
            "source": [],
        })

    df = df.copy()
    if "type" not in df.columns:
        df["type"] = "NFR"
    if "subclass" not in df.columns:
        df["subclass"] = "Unknown"
    if "source" not in df.columns:
        df["source"] = "merged"

    df = df.loc[:, ~df.columns.duplicated()]
    df.reset_index(drop=True, inplace=True)
    return df


# =========================================================
# ✅ PIPELINE FINAL (ACEITA FILES DIRETAMENTE)
# =========================================================
def run_pipeline(files: Iterable[FileLike]) -> pd.DataFrame:
    """Run the full merge pipeline for uploaded files."""
    dfs: List[pd.DataFrame] = []

    for f in files:
        df = read_uploaded_file(f)
        if df is not None:
            dfs.append(df)

    merged = unify_files(dfs)
    merged = finalize_dataset(merged)

    logger.info("Total rows: %s", len(merged))
    if "source" in merged.columns:
        logger.info("Rows by file:\n%s", merged["source"].value_counts())

    return merged

