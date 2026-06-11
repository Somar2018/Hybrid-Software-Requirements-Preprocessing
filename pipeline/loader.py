import logging
from pathlib import Path
from typing import Any, Iterable, List, Optional, TextIO, Union

import pandas as pd
import pytesseract
import fitz
from PIL import Image
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)

FileLike = Union[Path, str, TextIO, Any]
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}
TEXT_COLUMN_ALIASES = {
    "requirement_text": "text",
    "requirement text": "text",
    "description": "text",
    "text": "text",
}


# =====================================================
# ✅ LEITOR UNIVERSAL
# =====================================================
def _resolve_path(file: FileLike) -> Optional[Path]:
    if isinstance(file, Path):
        return file
    if isinstance(file, str):
        return Path(file)
    return None


def _normalize_name(file: FileLike) -> str:
    path = _resolve_path(file)
    if path is not None:
        return path.name.lower()
    return str(getattr(file, "name", "")).lower()


def _open_binary(file: FileLike) -> Optional[bytes]:
    if isinstance(file, (Path, str)):
        return Path(file).read_bytes()

    try:
        file.seek(0)
        return file.read()
    except Exception as exc:
        logger.warning("Unable to read binary file: %s", exc)
        return None


def read_file_safe(file: FileLike) -> Optional[pd.DataFrame]:
    """Read common file formats and return a DataFrame with a single text column."""
    name = _normalize_name(file)
    ext = Path(name).suffix.lower()

    try:
        if ext == ".csv":
            return pd.read_csv(file, sep=None, engine="python")

        if ext in {".xlsx", ".xls"}:
            return pd.read_excel(file)

        if ext == ".pdf":
            raw = _open_binary(file)
            if raw is None:
                return None

            text = ""
            try:
                doc = fitz.open(stream=raw, filetype="pdf")
                for page in doc:
                    text += page.get_text()
            except Exception as exc:
                logger.debug("PyMuPDF extraction failed: %s", exc)

            if not text.strip():
                try:
                    images = convert_from_bytes(raw)
                    for img in images:
                        text += pytesseract.image_to_string(img)
                except Exception as exc:
                    logger.error("PDF OCR fallback failed: %s", exc)

            if not text.strip():
                logger.warning("Empty PDF after extraction: %s", name)
                return None

            return pd.DataFrame({"text": text.splitlines()})

        if ext == ".txt":
            if isinstance(file, (Path, str)):
                text = Path(file).read_text(encoding="utf-8", errors="ignore")
            else:
                raw = file.read()
                text = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
            return pd.DataFrame({"text": text.splitlines()})

        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            img = Image.open(file)
            text = pytesseract.image_to_string(img)
            return pd.DataFrame({"text": text.splitlines()})

        logger.warning("Unsupported file format: %s", name)
        return None

    except Exception as exc:
        logger.error("Failed to read %s: %s", name, exc)
        return None


# =====================================================
# ✅ PIPELINE (MANTIDO)
# =====================================================

def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def _map_text_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mapping = {col: TEXT_COLUMN_ALIASES[col] for col in df.columns if col in TEXT_COLUMN_ALIASES}
    if mapping:
        df.rename(columns=mapping, inplace=True)
    return df


def direto(files: Iterable[FileLike]) -> pd.DataFrame:
    dfs: List[pd.DataFrame] = []

    for idx, f in enumerate(files):
        name = _normalize_name(f)
        logger.info("Processing file: %s", name)

        df = read_file_safe(f)
        if df is None or df.empty:
            logger.warning("Skipping file because it could not be read or is empty: %s", name)
            continue

        df = df.copy().dropna(axis=1, how="all")
        df = _normalize_dataframe_columns(df)
        df = _map_text_column(df)

        if "text" not in df.columns:
            logger.warning("No text column found in %s", name)
            continue

        df = df[df["text"].astype(str).str.strip() != ""]
        if df.empty:
            logger.warning("No valid text rows after cleaning: %s", name)
            continue

        df["global_id"] = [f"F{idx}_REQ_{i:05d}" for i in range(len(df))]
        df["source"] = name
        dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=["global_id", "text", "source"])
    return pd.concat(dfs, ignore_index=True)


def finalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    df = df.copy()
    if "type" not in df.columns:
        df["type"] = "NFR"
    if "subclass" not in df.columns:
        df["subclass"] = "Unknown"
    if "source" not in df.columns:
        df["source"] = "merged"
    df.reset_index(drop=True, inplace=True)
    return df


def run_pipeline(files: Iterable[FileLike]) -> pd.DataFrame:
    df = direto(files)
    df = finalize_dataset(df)
    logger.info("Total rows: %s", len(df))
    if not df.empty and "source" in df.columns:
        logger.info("Rows by file:\n%s", df["source"].value_counts())
    return df