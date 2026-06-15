# ============================================================
# myutils/io.py — FINAL FULL + STABLE VERSION
# ============================================================

import io
import re
from pathlib import Path
from typing import Union, Optional, BinaryIO, Dict, Any

import fitz
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image


# ============================================================
# 1) EXTRAÇÃO DE TABELAS
# ============================================================

def extract_pdf_tables_from_bytes(raw_bytes: bytes) -> Optional[pd.DataFrame]:
    try:
        rows = []
        header = None

        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    continue

                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    if header is None:
                        header = [
                            (c.strip() if isinstance(c, str) else f"col_{i}")
                            for i, c in enumerate(table[0])
                        ]

                    for row in table[1:]:
                        clean_row = [
                            (c.strip() if isinstance(c, str) else "")
                            for c in (row or [])
                        ]
                        clean_row = (clean_row + [""] * len(header))[:len(header)]
                        rows.append(clean_row)

        if not rows or header is None:
            return None

        return pd.DataFrame(rows, columns=header)

    except Exception:
        return None


# ============================================================
# 2) EXTRAÇÃO DE TEXTO (FITZ)
# ============================================================

def extract_pdf_text(raw: bytes) -> str:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        pages = []

        for page in doc:
            t1 = page.get_text("text") or ""
            blocks = page.get_text("blocks") or []
            t2 = " ".join([b[4] for b in blocks if isinstance(b, (list, tuple))])

            rawdict = page.get_text("rawdict") or {}
            t3_parts = []
            for block in rawdict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        t3_parts.append(span.get("text", ""))
            t3 = " ".join(t3_parts)

            t4 = page.get_text("html") or ""

            combined = f"{t1}\n{t2}\n{t3}\n{t4}"
            combined = re.sub(r"\s+", " ", combined)

            pages.append(combined.strip())

        return "\n".join(pages).strip()

    except Exception:
        return ""


# ============================================================
# 3) OCR
# ============================================================

def extract_pdf_ocr(raw: bytes) -> str:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        out = []

        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            out.append(pytesseract.image_to_string(img, lang="eng+por"))

        return "\n".join(out).strip()

    except Exception:
        return ""


# ============================================================
# 4) EXTRATOR UNIFICADO
# ============================================================

def extract_pdf_unified(pdf_path: str) -> dict:
    text_parts = []

    # 1) PyMuPDF / fitz
    try:
        import fitz

        doc = fitz.open(pdf_path)
        for page in doc:
            page_text = page.get_text("text") or ""
            if page_text.strip():
                text_parts.append(page_text)
        doc.close()

        text = "\n".join(text_parts).strip()
        if text:
            return {"text": text, "method": "pymupdf"}

    except Exception as e:
        print("[PDF] PyMuPDF falhou:", e)

    # 2) pdfplumber
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)

        text = "\n".join(text_parts).strip()
        if text:
            return {"text": text, "method": "pdfplumber"}

    except Exception as e:
        print("[PDF] pdfplumber falhou:", e)

    # 3) pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)

        text = "\n".join(text_parts).strip()
        if text:
            return {"text": text, "method": "pypdf"}

    except Exception as e:
        print("[PDF] pypdf falhou:", e)

    return {"text": "", "method": "none"}


# ============================================================
# 5) NORMALIZAÇÃO
# ============================================================

def normalize_output(data: Any, source_type: str = "unknown") -> pd.DataFrame:
    if isinstance(data, dict):
        return pd.DataFrame([{
            "text": data.get("text", ""),
            "has_ocr": data.get("has_ocr", False),
            "source_type": source_type,
            "tables": data.get("tables"),
        }])

    if isinstance(data, str):
        return pd.DataFrame([{
            "text": data,
            "has_ocr": False,
            "source_type": source_type,
        }])

    if isinstance(data, pd.DataFrame):
        if "text" not in data.columns:
            data["text"] = ""
        data["source_type"] = source_type
        return data

    return pd.DataFrame([{
        "text": "",
        "has_ocr": False,
        "source_type": source_type,
    }])


# ============================================================
# 6) LEITOR UNIVERSAL
# ============================================================

def read_file_safe(file: Union[str, Path, BinaryIO]) -> pd.DataFrame:
    opened_here = False

    if isinstance(file, (str, Path)):
        file = open(file, "rb")
        opened_here = True

    name = getattr(file, "name", "").lower()

    try:
        file.seek(0)

        if name.endswith(".pdf"):
            raw = file.read()
            data = extract_pdf_unified(raw)
            return normalize_output(data, "pdf")

        if name.endswith((".png", ".jpg", ".jpeg", ".tiff", ".tif")):
            img = Image.open(file)
            if img.mode != "RGB":
                img = img.convert("RGB")
            text = pytesseract.image_to_string(img, lang="eng+por")
            return normalize_output(text, "image")

        if name.endswith(".txt"):
            text = file.read().decode("utf-8", errors="ignore")
            return normalize_output(text, "txt")

        if name.endswith(".csv"):
            df = pd.read_csv(file, engine="python", on_bad_lines="skip")
            return normalize_output(df, "csv")

        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file, engine="openpyxl")
            return normalize_output(df, "excel")

        return normalize_output("", "unknown")

    except Exception as e:
        print(f"[READ ERROR] {name}: {e}")
        return normalize_output("", "error")

    finally:
        if opened_here:
            file.close()

def prepare_input_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante que o DataFrame tem as colunas necessárias e limpa dados.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=["global_id", "text"])

    df = df.copy()

    # Normaliza colunas
    if "id" in df.columns and "global_id" not in df.columns:
        df["global_id"] = df["id"]

    if "requirement" in df.columns and "text" not in df.columns:
        df["text"] = df["requirement"]

    # Garante colunas essenciais
    if "global_id" not in df.columns:
        df["global_id"] = range(1, len(df) + 1)

    if "text" not in df.columns:
        df["text"] = ""

    # Limpeza básica
    df["global_id"] = df["global_id"].astype(str)
    df["text"] = df["text"].astype(str).str.strip()

    # Remove linhas vazias
    df = df[df["text"].str.len() > 3]

    return df.reset_index(drop=True)

from typing import Optional, Tuple

def heuristic_classify(text: str) -> Optional[Tuple[str, str]]:
    if not text:
        return None

    t = text.lower()

    # -------------------------
    # ✅ NFR DETECTION (PRIMEIRO!)
    # -------------------------

    # Performance
    if any(k in t for k in [
        "performance", "response time", "latency",
        "throughput", "concurrent users", "1000 users"
    ]):
        return "NFR", "Performance"

    # Availability
    if any(k in t for k in [
        "24 hours", "24/7", "availability", "uptime"
    ]):
        return "NFR", "Availability"

    # Reliability
    if any(k in t for k in [
        "backup", "recover", "restore", "failure", "failover"
    ]):
        return "NFR", "Reliability"

    # Security
    if any(k in t for k in [
        "security", "authentication", "authorization",
        "access control", "privacy"
    ]):
        return "NFR", "Security"

    # Usability
    if any(k in t for k in [
        "user interface", "usable", "easy to use",
        "responsive interface", "user-friendly"
    ]):
        return "NFR", "Usability"

    # Scalability
    if any(k in t for k in [
        "scalable", "scale", "expand"
    ]):
        return "NFR", "Scalability"

    # -------------------------
    # ✅ FUNCTIONAL
    # -------------------------
    if any(k in t for k in [
        "shall", "must", "allow", "provide", "enable"
    ]):
        return "FR", "Functional"

    return None

def detect_misclassification(req, predicted_class, dominant_classes, confidence=None):
    reasons = []
    flagged = False
    req_lower = req.lower()

    # ✅ força entrada de Unknown
    if predicted_class in ["Unknown", "UNK"]:
        flagged = True
        reasons.append("unknown_force")

    # ✅ classe dominante
    if predicted_class in dominant_classes:
        flagged = True
        reasons.append("dominant_force")

    # ✅ comprimento
    if len(req) < 20:
        flagged = True
        reasons.append("too_short")

    if len(req) > 300:
        flagged = True
        reasons.append("too_long")

    return flagged, reasons