# ============================================================
# PDF EXTRACTION — FINAL UNIFIED PIPELINE
# ============================================================

import io
import re
import fitz
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd

from myutils.text import (
    limpar,
    reconstruir,
    extrair_requisitos_brutos,
    hybrid_classification,
)


# ============================================================
# 1) NOISE FILTER
# ============================================================
def _is_noise(line: str) -> bool:
    line = line.strip()

    if not line:
        return True

    if len(line) < 4:
        return True

    if "PAGE LEFT INTENTIONALLY BLANK" in line.upper():
        return True

    if re.match(r"^Page\s+\d+", line, re.IGNORECASE):
        return True

    if re.fullmatch(r"[\d\s\-]+", line):
        return True

    return False


def _clean_lines(text: str):
    return [
        l.strip()
        for l in text.splitlines()
        if l.strip() and not _is_noise(l)
    ]


# ============================================================
# 2) PDFPLUMBER
# ============================================================
def _extract_pdfplumber(raw: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n".join(pages)
    except:
        return ""


# ============================================================
# 3) FITZ
# ============================================================
def _extract_fitz(raw: bytes) -> str:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return "\n".join(pages)
    except:
        return ""


# ============================================================
# 4) OCR
# ============================================================
def _extract_ocr(raw: bytes) -> str:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        out = []

        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            out.append(pytesseract.image_to_string(img, lang="eng+por"))

        doc.close()
        return "\n".join(out)
    except:
        return ""


# ============================================================
# 5) UNIFIED PDF EXTRACTOR
# ============================================================
def extract_pdf_unified_final(raw: bytes) -> str:
    text = _extract_pdfplumber(raw)

    if len(text.strip()) < 80:
        text = _extract_fitz(raw)

    if len(text.strip()) < 80:
        text = _extract_ocr(raw)

    lines = _clean_lines(text)
    paragraphs = reconstruir(lines)

    return "\n".join(paragraphs)


# ============================================================
# 6) REQUIREMENT PIPELINE
# ============================================================
def extract_requirements_from_pdf(raw: bytes) -> pd.DataFrame:
    text = extract_pdf_unified_final(raw)

    # 1) Extrair requisitos brutos
    reqs = extrair_requisitos_brutos(text)

    # 2) Limpar
    reqs = [limpar(r) for r in reqs]

    # 3) Classificar
    rows = []
    for r in reqs:
        cls = hybrid_classification(r) or ("FR", "General")
        rows.append({
            "text": r,
            "type": cls[0],
            "subclass": cls[1],
        })

    return pd.DataFrame(rows)
