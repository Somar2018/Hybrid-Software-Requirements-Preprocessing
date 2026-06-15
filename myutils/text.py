# ============================================================
# myutils/text.py — FINAL CLEAN VERSION
# ============================================================

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# ============================================================
# CLEAN TEXT
# ============================================================
def limpar(txt: str) -> str:
    if not txt or not isinstance(txt, str):
        return ""

    txt = str(txt)

    txt = re.sub(r"Software Requirements Specification.*", "", txt, flags=re.I)
    txt = re.sub(r"Page\s+\d+", "", txt, flags=re.I)
    txt = re.sub(r"\s+", " ", txt)

    return txt.strip()


def limpar_prefixo(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"^(OE|CO|UD)-\d+:\s*", "", text)
    text = re.sub(r"Req ID:\s*\d+.*?Description:\s*", "", text, flags=re.I)

    return text.strip()


# ============================================================
# LINE VALIDATION
# ============================================================
def linha_valida(line: str) -> bool:
    if not line or not isinstance(line, str):
        return False

    line = line.strip()

    if not line:
        return False

    if len(line) < 10:
        return False

    if line.startswith("%") or line.startswith("@"):
        return False

    if "====" in line or "%%%%" in line:
        return False

    if "http://" in line or "https://" in line:
        return False

    return True


# ============================================================
# SPLIT INTO BLOCKS
# ============================================================
def dividir(txt: str) -> List[str]:
    if not txt:
        return []

    blocos = re.split(r"(?=(OE-\d+:|CO-\d+:|UD-\d+:|Req ID:))", txt)

    linhas: List[str] = []
    for bloco in blocos:
        bloco = bloco.strip()
        if bloco and linha_valida(bloco):
            linhas.append(bloco)

    return linhas


# ============================================================
# RECONSTRUCT MULTILINE REQUIREMENTS
# ============================================================
def reconstruir(linhas: List[str]) -> List[str]:
    if not linhas:
        return []

    resultado: List[str] = []
    buffer = ""

    for line in linhas:
        line = line.strip()

        if re.match(r"^(OE|CO|UD)-\d+:", line):
            if buffer:
                resultado.append(buffer)
            buffer = line
            continue

        if buffer and not line[0].isupper():
            buffer += " " + line
        else:
            if buffer:
                resultado.append(buffer)
            buffer = line

    if buffer:
        resultado.append(buffer)

    return resultado


# ============================================================
# STRONG SEMANTIC REQUIREMENT FILTER
# ============================================================
def is_real_requirement(text: str) -> bool:
    if not text:
        return False

    t = text.strip().lower()

    bad_start = [
        "software specification",
        "general description",
        "introduction",
        "overview",
        "purpose",
        "scope",
        "this specification",
        "this document",
        "growing demand",
        "centralize project management",
    ]
    if any(t.startswith(b) for b in bad_start):
        return False

    bad_keywords = [
        "is an integrated solution",
        "provides an initial foundation",
        "organizations face",
        "as companies grow",
        "promoting team collaboration",
    ]
    if any(b in t for b in bad_keywords):
        return False

    actions = [
        "shall", "must", "should",
        "allow", "enable", "provide",
        "support", "manage", "track",
        "create", "define", "authenticate",
        "authorize", "store", "process",
    ]
    if not any(a in t for a in actions):
        return False

    if t.endswith(":") or t.endswith(",") or t.endswith(";"):
        return False

    if len(t.split()) < 5:
        return False

    return True


# ============================================================
# NORMALIZATION (NO SHALL FORCING)
# ============================================================
def normalize_requirement(text: str) -> str:
    t = text.strip()

    t = re.sub(r"^\d+(\.\d+)*\s*", "", t)
    t = re.sub(r"^[\-\•]\s*", "", t)

    if not t.endswith("."):
        t += "."

    return t[0].upper() + t[1:]


# ============================================================
# RAW REQUIREMENT EXTRACTION
# ============================================================
def extrair_requisitos_brutos(text: str) -> List[str]:
    if not text:
        return []

    linhas = dividir(text)
    linhas = [limpar(l) for l in linhas]
    linhas = [limpar_prefixo(l) for l in linhas]

    linhas = [l for l in linhas if is_real_requirement(l)]

    seen = set()
    clean: List[str] = []

    for line in linhas:
        key = line.lower().strip()
        if key not in seen:
            seen.add(key)
            clean.append(line)

    return clean


# ============================================================
# HYBRID CLASSIFICATION
# ============================================================
def hybrid_classification(text: str) -> Optional[Tuple[str, str]]:
    if not text:
        return None

    t = text.lower()

    if any(k in t for k in ["authentication", "authorization", "encrypt", "secure"]):
        return "NFR", "Security"

    if any(k in t for k in ["latency", "response time", "throughput", "bandwidth"]):
        return "NFR", "Performance"

    if "shall" in t or "must" in t:
        return "FR", "Functional"

    return "FR", "General"
