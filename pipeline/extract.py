import os
import re
import tempfile
from collections import Counter
from typing import Dict, Any

import pandas as pd

from myutils.io import read_file_safe, extract_pdf_unified
from myutils.text import (
    reconstruir,
    extrair_requisitos_brutos,
    hybrid_classification,
    normalize_requirement,
)


OUTPUT_COLUMNS = ["text", "type", "subclass"]


MODAL_PATTERN = re.compile(
    r"\b("
    r"must|shall|should|"
    r"is required to|are required to|will be required to|"
    r"deve|deverá|devem|obrigatório|obrigatória"
    r")\b",
    re.IGNORECASE,
)


BAD_START_PATTERN = re.compile(
    r"^("
    r"this|these|although|due to|for this requirement|"
    r"one of the|the goal|the priorities|"
    r"moodle\)|puget sound|"
    r"system administrators are primarily|"
    r"a freely available|back-up requirements|"
    r"relevant, online|"
    r"the social|"
    r"the initial production release|"
    r"this information|"
    r"this statement provides"
    r")\b",
    re.IGNORECASE,
)


NOISE_TERMS = [
    "confidential",
    "software requirements specification",
    "table of contents",
    "revision history",
    "copyright",
    "document version",
    "moodle version",
]


def empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def extract_text_from_pdf_upload(file) -> str:
    file.seek(0)
    raw_bytes = file.read()

    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        pdf_data = extract_pdf_unified(tmp_path)

        if isinstance(pdf_data, dict):
            return str(pdf_data.get("text", "") or "")

        if isinstance(pdf_data, str):
            return pdf_data

        if isinstance(pdf_data, pd.DataFrame) and "text" in pdf_data.columns:
            return "\n".join(pdf_data["text"].astype(str).tolist())

        if isinstance(pdf_data, list):
            return "\n".join(str(x) for x in pdf_data)

        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def clean_pdf_noise(texto: str) -> str:
    texto = texto.replace("\x00", " ")
    texto = texto.replace("\uf0a7", " ")
    texto = texto.replace("�", " ")
    texto = re.sub(r"[^\S\n]+", " ", texto)

    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    cleaned = []

    for linha in linhas:
        low = linha.lower()

        if any(term in low for term in NOISE_TERMS):
            continue

        if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", low):
            continue

        if re.fullmatch(r"\d+", low):
            continue

        if re.search(r"\bdate:\s*\d{1,2}/\d{1,2}/\d{2,4}", low):
            continue

        if re.search(r"\bversion:\s*\d", low):
            continue

        if len(linha) < 8:
            continue

        cleaned.append(linha)

    return "\n".join(cleaned)


def remove_repeated_lines(texto: str, max_repeats: int = 2) -> str:
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    counts = Counter(linhas)

    return "\n".join(
        linha for linha in linhas
        if counts[linha] <= max_repeats
    )


def split_numbered_requirements(texto: str) -> list[str]:
    texto = re.sub(r"\s+", " ", texto).strip()

    parts = re.split(r"(?=\b\d+\.\d+\.\d+\s+)", texto)
    results = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        part = re.sub(r"^\d+\.\d+\.\d+\s+", "", part).strip()
        results.extend(split_requirement_sentences(part))

    return results


def split_requirement_sentences(texto: str) -> list[str]:
    texto = re.sub(r"\s+", " ", texto).strip()

    sentences = re.split(
        r"(?<=[.!?])\s+"
        r"(?=(The|A|An|Actors|Students|Users|System|Course|No|This)\b)",
        texto,
    )

    cleaned = []

    for item in sentences:
        item = item.strip()

        if not item:
            continue

        if item in {
            "The", "A", "An", "Actors", "Students",
            "Users", "System", "Course", "No", "This"
        }:
            continue

        cleaned.append(item)

    return cleaned


def looks_like_noise(texto: str) -> bool:
    text = re.sub(r"\s+", " ", str(texto)).strip()
    low = text.lower()

    if len(text) < 25:
        return True

    if any(term in low for term in NOISE_TERMS):
        return True

    if BAD_START_PATTERN.search(text):
        return True

    if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", low):
        return True

    return False


def is_normative_requirement(texto: str) -> bool:
    text = re.sub(r"\s+", " ", str(texto)).strip()

    if looks_like_noise(text):
        return False

    if not MODAL_PATTERN.search(text):
        return False

    useful_subjects = [
        "system",
        "user",
        "users",
        "actor",
        "actors",
        "student",
        "students",
        "administrator",
        "administrators",
        "course administrator",
        "application",
        "software",
        "documentation",
    ]

    low = text.lower()

    if not any(subject in low for subject in useful_subjects):
        return False

    return True


def extract_candidate_requirements(texto: str) -> list[str]:
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    linhas = reconstruir(linhas)

    candidates = []

    # 1) Primeiro tenta o extrator existente
    raw_reqs = extrair_requisitos_brutos("\n".join(linhas))

    for req in raw_reqs:
        candidates.extend(split_numbered_requirements(req))

    # 2) Depois tenta diretamente nas linhas reconstruídas
    for linha in linhas:
        candidates.extend(split_numbered_requirements(linha))

    clean = []

    for req in candidates:
        req = normalize_requirement(req)
        req = re.sub(r"\s+", " ", req).strip()

        if is_normative_requirement(req):
            clean.append(req)

    return list(dict.fromkeys(clean))


def classify_requirement(texto: str):
    low = texto.lower()

    nfr_keywords = {
        "Performance": [
            "concurrent users",
            "performance",
            "load",
            "response time",
            "latency",
            "throughput",
        ],
        "Reliability": [
            "available",
            "availability",
            "backup",
            "backed up",
            "restore",
            "offline",
            "uptime",
            "up-time",
        ],
        "Usability": [
            "simple",
            "responsive interface",
            "easy-to-use",
            "user interface",
            "help",
            "documentation",
        ],
        "Security": [
            "authentication",
            "authorization",
            "access",
            "permission",
            "login",
            "password",
        ],
        "Maintainability": [
            "maintainable",
            "maintenance",
            "troubleshooting",
            "configuration",
        ],
    }

    for subclass, keywords in nfr_keywords.items():
        if any(k in low for k in keywords):
            return "NFR", subclass

    result = hybrid_classification(texto)

    if result and isinstance(result, tuple) and len(result) == 2:
        return result

    return "FR", "Functional"


def process_file(file, idx: int, ctx: Dict[str, Any]) -> pd.DataFrame:
    print(f"[PROCESS] Arquivo {idx + 1}: {getattr(file, 'name', '')}")

    filename = getattr(file, "name", "").lower()

    if filename.endswith(".pdf"):
        source = "pdf"
        texto = extract_text_from_pdf_upload(file)
    else:
        df = read_file_safe(file)
        source = df.get("source_type", ["unknown"])[0]

        if "text" in df.columns:
            texto = " ".join(df["text"].astype(str).tolist()).strip()
        else:
            texto = ""

    print("[DEBUG] source:", source)
    print("[DEBUG] tamanho texto original:", len(texto))

    if len(texto.strip()) < 20:
        print("[WARN] Texto insuficiente após extração. O PDF pode ser imagem/digitalizado.")
        return empty_result()

    texto = clean_pdf_noise(texto)
    texto = remove_repeated_lines(texto)

    print("[DEBUG] tamanho texto limpo:", len(texto))

    reqs = extract_candidate_requirements(texto)

    print("[DEBUG] requisitos finais:", len(reqs))
    print("[DEBUG] preview requisitos:", reqs[:5])

    rows = []

    for req in reqs:
        tipo, subclass = classify_requirement(req)

        rows.append({
            "text": req,
            "type": tipo,
            "subclass": subclass,
        })

    if not rows:
        return empty_result()

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def run_pipeline(files, ctx) -> pd.DataFrame:
    all_rows = []

    for i, file in enumerate(files):
        result = process_file(file, i, ctx)

        if result is not None and not result.empty:
            all_rows.append(result)

    if all_rows:
        final = pd.concat(all_rows, ignore_index=True)
    else:
        final = empty_result()

    for col in OUTPUT_COLUMNS:
        if col not in final.columns:
            final[col] = ""

    final["text"] = final["text"].astype(str).str.strip()
    final = final[final["text"] != ""]

    final["text_clean_key"] = (
        final["text"]
        .astype(str)
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    final = final.drop_duplicates(subset=["text_clean_key"])
    final = final.drop(columns=["text_clean_key"])

    return final[OUTPUT_COLUMNS]