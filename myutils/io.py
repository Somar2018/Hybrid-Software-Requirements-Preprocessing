import io
import re
from pathlib import Path
from typing import Union, Optional, BinaryIO, Dict, Any

import fitz
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes


# ============================================================
# 1) EXTRAÇÃO DE TABELAS
# ============================================================
def extract_pdf_tables_from_bytes(raw_bytes: bytes) -> Optional[pd.DataFrame]:
    rows = []
    header = None

    try:
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
# 2) TEXTO PDF
# ============================================================
def extract_pdf_text(raw: bytes) -> str:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        pages = []

        for page in doc:
            text = page.get_text("text") or ""
            text = text.replace("-\n", "")
            text = re.sub(r"\n+", " ", text)
            text = re.sub(r"\s+", " ", text)
            pages.append(text.strip())

        return "\n".join(pages).strip()

    except Exception:
        return ""


# ============================================================
# 3) OCR
# ============================================================
def extract_pdf_ocr(raw: bytes) -> str:
    try:
        images = convert_from_bytes(raw, dpi=300)
        out = []

        for img in images:
            if img.mode != "RGB":
                img = img.convert("RGB")
            out.append(pytesseract.image_to_string(img, lang="eng+por"))

        return "\n".join(out).strip()

    except Exception:
        return ""


# ============================================================
# 4) EXTRAÇÃO UNIFICADA (SEMPRE MESMO FORMATO)
# ============================================================
def extract_pdf_unified(raw_bytes: bytes) -> Dict[str, Any]:
    tables = extract_pdf_tables_from_bytes(raw_bytes)
    text = extract_pdf_text(raw_bytes)

    has_ocr = False

    if len(text.strip()) < 80:
        text = extract_pdf_ocr(raw_bytes)
        has_ocr = True

    return {
        "text": text or "",
        "tables": tables,
        "has_ocr": has_ocr,
        "source_type": "pdf"
    }


# ============================================================
# 5) NORMALIZAÇÃO (CHAVE PARA EVITAR TEU ERRO)
# ============================================================
def normalize_output(data: Any, source_type: str = "unknown") -> pd.DataFrame:
    """
    Garante SEMPRE DataFrame com coluna 'text'
    """

    # dict (PDF)
    if isinstance(data, dict):
        return pd.DataFrame([{
            "text": data.get("text", ""),
            "has_ocr": data.get("has_ocr", False),
            "source_type": source_type,
            "tables": data.get("tables")
        }])

    # string (txt / OCR)
    if isinstance(data, str):
        return pd.DataFrame([{
            "text": data,
            "has_ocr": False,
            "source_type": source_type
        }])

    # DataFrame direto (csv/excel)
    if isinstance(data, pd.DataFrame):
        if "text" not in data.columns:
            data["text"] = ""
        data["source_type"] = source_type
        return data

    return pd.DataFrame([{
        "text": "",
        "has_ocr": False,
        "source_type": source_type
    }])


# ============================================================
# 6) LEITOR UNIVERSAL
# ============================================================
def read_file_safe(file: Union[str, Path, BinaryIO]) -> pd.DataFrame:
    opened_here = False

    if isinstance(file, (str, Path)):
        file = open(file, "rb")
        opened_here = True

    name = getattr(file, "name", "file").lower()

    try:
        file.seek(0)

        # ---------------- PDF ----------------
        if name.endswith(".pdf"):
            raw = file.read()
            data = extract_pdf_unified(raw)
            return normalize_output(data, "pdf")

        # ---------------- IMAGE ----------------
        if name.endswith((".png", ".jpg", ".jpeg", ".tiff", ".tif")):
            img = Image.open(file)
            if img.mode != "RGB":
                img = img.convert("RGB")
            text = pytesseract.image_to_string(img, lang="eng+por")
            return normalize_output(text, "image")

        # ---------------- TXT ----------------
        if name.endswith(".txt"):
            text = file.read().decode("utf-8", errors="ignore")
            return normalize_output(text, "txt")

        # ---------------- CSV ----------------
        if name.endswith(".csv"):
            df = pd.read_csv(file, engine="python", on_bad_lines="skip")
            return normalize_output(df, "csv")

        # ---------------- EXCEL ----------------
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