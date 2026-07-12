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

        # =====================================================
        # CSV
        # =====================================================
        if name.endswith(".csv"):

            separators = [",", ";", "\t", "|"]

            for sep in separators:

                try:

                    f.seek(0)

                    df = pd.read_csv(
                        f,
                        sep=sep,
                        encoding="utf-8",
                        on_bad_lines="skip"
                    )

                    if len(df.columns) > 1:
                        return df

                except Exception:
                    pass

            # Última tentativa
            try:

                f.seek(0)

                return pd.read_csv(
                    f,
                    engine="python",
                    encoding="utf-8",
                    on_bad_lines="skip"
                )

            except Exception as exc:

                logger.error(
                    "Failed to read uploaded file %s: %s",
                    getattr(f, "name", str(f)),
                    exc
                )

                return None

        # =====================================================
        # EXCEL
        # =====================================================
        if name.endswith((".xlsx", ".xls")):

            f.seek(0)

            return pd.read_excel(f)

        # =====================================================
        # NÃO SUPORTADO
        # =====================================================
        logger.warning(
            "Unsupported upload format: %s",
            name
        )

        return None

    except Exception as exc:

        logger.error(
            "Failed to read uploaded file %s: %s",
            getattr(f, "name", str(f)),
            exc
        )

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

        if (
            df is None
            or not isinstance(df, pd.DataFrame)
            or df.empty
        ):
            continue

        # -----------------------------------------
        # Normaliza nomes das colunas
        # -----------------------------------------
        df = _normalize_columns(df)

        # Remove colunas vazias do Excel (Unnamed)
        df = df.loc[
            :,
            ~df.columns.str.contains(
                r"^unnamed",
                case=False,
                regex=True
            )
        ]

        # Remove colunas duplicadas existentes
        if not df.columns.is_unique:

            logger.warning(
                "Duplicate columns found in dataset %s: %s",
                idx + 1,
                df.columns[df.columns.duplicated()].tolist()
            )

            df = df.loc[:, ~df.columns.duplicated()]

        # -----------------------------------------
        # Procura coluna de texto
        # -----------------------------------------
        text_col = _find_text_column(df)

        if text_col is None:

            df["text"] = ""

        elif text_col != "text":

            # evita criar duas colunas chamadas "text"
            if "text" in df.columns:
                df.drop(columns=["text"], inplace=True)

            df.rename(
                columns={text_col: "text"},
                inplace=True
            )

        if "text" not in df.columns:
            df["text"] = ""

        df["text"] = (
            df["text"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # Remove novamente caso o rename tenha criado duplicados
        df = df.loc[:, ~df.columns.duplicated()]

        # Reset do índice
        df.reset_index(drop=True, inplace=True)

        if df.empty:
            continue

        # -----------------------------------------
        # IDs únicos
        # -----------------------------------------
        df["id"] = [
            f"REQ_{idx + 1:03d}_{i:06d}"
            for i in range(1, len(df) + 1)
        ]

        if "file_index" not in df.columns:
            df["file_index"] = idx + 1

        # -----------------------------------------
        # Diagnóstico
        # -----------------------------------------
        logger.info(
            "Dataset %s | rows=%s | cols=%s",
            idx + 1,
            len(df),
            len(df.columns)
        )

        clean_dfs.append(df)

    if not clean_dfs:

        return pd.DataFrame(
            columns=[
                "global_id",
                "text",
                "type",
                "subclass",
                "file_index"
            ]
        )

    # ==========================================
    # Última verificação antes do concat
    # ==========================================
    for i, df in enumerate(clean_dfs):

        if not df.columns.is_unique:

            logger.error(
                "Dataset %s still has duplicate columns: %s",
                i + 1,
                df.columns[df.columns.duplicated()].tolist()
            )

            df = df.loc[:, ~df.columns.duplicated()]
            clean_dfs[i] = df

        df.reset_index(drop=True, inplace=True)

    # ==========================================
    # Concat robusto
    # ==========================================
    merged = pd.concat(
        clean_dfs,
        axis=0,
        join="outer",
        ignore_index=True,
        sort=False,
        copy=False
    )

    merged = merged.loc[:, ~merged.columns.duplicated()]
    merged.reset_index(drop=True, inplace=True)

    return merged


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
            "file_index": []
        })

    df = df.copy()

    if "type" not in df.columns:
        df["type"] = "NFR"

    if "subclass" not in df.columns:
        df["subclass"] = "Unknown"

    if "file_index" not in df.columns:
        df["file_index"] = 0

    df = df.loc[:, ~df.columns.duplicated()]
    df.reset_index(drop=True, inplace=True)

    return df


# =========================================================
# ✅ PIPELINE FINAL (ACEITA FILES DIRETAMENTE)
# =========================================================
def run_pipeline(files):

    dfs = []

    for idx, f in enumerate(files, start=1):

        df = read_uploaded_file(f)

        if df is not None:

            df["project_id"] = f"P{idx:03d}"
            df["dataset_id"] = f"DS{idx:03d}"
            df["file_index"] = idx

            dfs.append(df)

    merged = unify_files(dfs)

    return finalize_dataset(merged)

