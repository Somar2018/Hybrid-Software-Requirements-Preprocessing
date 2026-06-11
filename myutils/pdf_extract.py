import io
import re
import fitz
import pdfplumber
import pytesseract
from PIL import Image


# SAFE IMPORTS (evita crash silencioso)
try:
    import fitz
except Exception as e:
    print("FITZ ERROR:", e)

try:
    import pdfplumber
except Exception as e:
    print("PDFPLUMBER ERROR:", e)

try:
    import pytesseract
except Exception as e:
    print("TESSERACT ERROR:", e)

from PIL import Image

# =========================================================
# NOISE DETECTION
# =========================================================
def is_noise(line: str) -> bool:
    line = line.strip()

    if not line:
        return True

    if len(line) < 4:
        return True

    if "PAGE LEFT INTENTIONALLY BLANK" in line.upper():
        return True

    if re.match(r"^Page\s+\d+", line, re.IGNORECASE):
        return True

    if re.match(r"^\d+\s+[A-Z]-\d+", line):
        return True

    if re.fullmatch(r"[\d\s\-]+", line):
        return True

    return False


# =========================================================
# CLEAN LINES
# =========================================================
def clean_lines(text: str):
    if not text:
        return []

    return [
        line.strip()
        for line in text.splitlines()
        if not is_noise(line.strip())
    ]


# =========================================================
# PARAGRAPH RECONSTRUCTION
# =========================================================
def reconstruct_paragraphs(lines):
    paragraphs = []
    buffer = ""

    for line in lines:

        is_new_block = (
            line.endswith(".")
            or line.endswith(":")
            or re.match(r"^[A-Z][A-Z\s]{5,}$", line)
        )

        buffer = (buffer + " " + line).strip()

        if is_new_block:
            paragraphs.append(buffer)
            buffer = ""

    if buffer:
        paragraphs.append(buffer)

    return paragraphs


# =========================================================
# PDFPLUMBER
# =========================================================
def extract_pdfplumber(file_input):
    try:
        if isinstance(file_input, (bytes, bytearray)):
            file_input = io.BytesIO(file_input)

        text_pages = []

        with pdfplumber.open(file_input) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    text_pages.append(txt)

        return "\n".join(text_pages)

    except Exception:
        return ""


# =========================================================
# FITZ
# =========================================================
def extract_fitz(file_input):
    try:
        if isinstance(file_input, (bytes, bytearray)):
            doc = fitz.open(stream=file_input, filetype="pdf")
        else:
            doc = fitz.open(file_input)

        text = "\n".join(page.get_text() for page in doc)
        doc.close()

        return text

    except Exception:
        return ""


# =========================================================
# OCR
# =========================================================
def extract_ocr(file_input):
    try:
        if isinstance(file_input, (bytes, bytearray)):
            doc = fitz.open(stream=file_input, filetype="pdf")
        else:
            doc = fitz.open(file_input)

        pages = []

        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))

            pages.append(
                pytesseract.image_to_string(img, lang="eng+por")
            )

        doc.close()

        return "\n".join(pages)

    except Exception:
        return ""


# =========================================================
# SMART PIPELINE
# =========================================================
def smart_extract_text(file_input):

    text = extract_pdfplumber(file_input)

    if len(text) < 80:
        text = extract_fitz(file_input)

    if len(text) < 80:
        text = extract_ocr(file_input)

    lines = clean_lines(text)
    paragraphs = reconstruct_paragraphs(lines)

    clean_text = "\n".join(paragraphs)

    requirements = [
        p.strip()
        for p in re.split(r"\n\s*\n|\n", clean_text)
        if len(p.strip()) > 6
    ]

    return {
        "text": clean_text,
        "requirements": requirements,
        "raw_text": text
    }


# =========================================================
# 🔥 COMPATIBILITY LAYER (CRÍTICO)
# =========================================================
def extract_pdf_robust(file_input):
    """
    Mantém compatibilidade com todo o teu pipeline antigo
    """
    return smart_extract_text(file_input)