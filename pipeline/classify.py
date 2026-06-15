from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd
import logging

from myutils.io import prepare_input_dataframe, heuristic_classify
from core.config import (
    VALID_CLASSES,
    DEFAULT_CLASS,
    DEFAULT_SUB,
    OUTPUT_COLUMNS,
    FREE_DETECT,
    ISO_MAP,
    BATCH_SIZE,
)

logger = logging.getLogger(__name__)


# =========================
# NORMALIZAÇÃO
# =========================
def normalizar_class(cls: str) -> str:
    if not cls:
        return DEFAULT_CLASS
    cls = cls.strip().upper()
    return cls if cls in VALID_CLASSES else DEFAULT_CLASS


def normalize_text(text: str) -> str:
    return str(text).replace("\n", " ").strip()


def detect_free_subclass(text: str) -> Optional[str]:
    t = text.lower()
    for key, sub in FREE_DETECT.items():
        if key in t:
            return sub
    return None


# =========================
# CLASSIFICADOR AVANÇADO ✅
# =========================
def advanced_classify(text: str) -> Tuple[Optional[str], Optional[str]]:
    low = text.lower()

    # FR (comportamento)
    if any(k in low for k in ["restricted to", "based on", "depending on"]):
        return "FR", "Functional"

    if any(k in low for k in [
        "shall", "must", "will", "provide",
        "allow", "display", "retrieve"
    ]) and not any(x in low for x in [
        "seconds", "%", "mb", "latency", "uptime", "memory"
    ]):
        return "FR", "Functional"

    # NFR - ISO
    if any(k in low for k in ["response time", "latency", "seconds", "throughput"]):
        return "NFR", "Performance"

    if any(k in low for k in ["memory", "storage", "mb", "cpu"]):
        return "NFR", "Performance"

    if any(k in low for k in ["uptime", "availability", "% of time"]):
        return "NFR", "Availability"

    if any(k in low for k in ["accuracy", "accurate", "reliable"]):
        return "NFR", "Reliability"

    if any(k in low for k in ["authentication", "authorization", "password"]):
        return "NFR", "Security"

    return None, None

def compute_confidence(text: str, cls: str, sub: str) -> float:
    score = 0.5  # base

    low = text.lower()

    # ✅ positivos
    if "shall" in low:
        score += 0.3

    if any(k in low for k in ["%", "seconds", "mb"]):
        score += 0.3

    if any(k in low for k in ["latency", "uptime", "memory"]):
        score += 0.2

    # ✅ negativos
    if "should" in low or "ideally" in low:
        score -= 0.3

    if len(text) < 20:
        score -= 0.2

    if sub == "Functional" and cls == "NFR":
        score -= 0.4  # inconsistente

    # limitar entre 0 e 1
    return max(0.0, min(1.0, round(score, 2)))


# =========================
# NORMALIZAÇÃO ISO
# =========================
def normalize_to_iso(sub: str, text: str) -> str:
    if not sub:
        return "Functional"

    if sub in ISO_MAP:
        return ISO_MAP[sub]

    detected = detect_free_subclass(text)
    if detected:
        return ISO_MAP.get(detected, detected)

    low = text.lower()

    if "%" in text or "uptime" in low:
        return "Availability"

    if "memory" in low or "mb" in low:
        return "Performance"

    return "Functional"


# =========================
# FALLBACK CORRETO ✅
# =========================
def smart_fallback(text: str) -> Tuple[str, str]:
    adv_cls, adv_sub = advanced_classify(text)
    if adv_cls:
        return adv_cls, adv_sub

    heur = heuristic_classify(text)
    if heur:
        return heur

    return "FR", "Functional"


# =========================
# LLM MOCK (seguro)
# =========================
def perguntar(prompt, client, model, provider, modo, cache):
    return ""


def classify_batch(
    batch_text: str,
    client: Any,
    model: str,
    provider: str,
    modo: str,
    cache: Optional[Dict[str, str]],
    batch_ids: Set[str],
) -> List[Tuple[str, str, str]]:
    return []


# =========================
# MAIN FUNCTION ✅ FINAL
# =========================
def classificar(df: pd.DataFrame, ctx: Dict[str, Any]) -> pd.DataFrame:

    df = prepare_input_dataframe(df)

    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    rows = df.to_dict("records")
    output = {}

    # =========================
    # PROCESSAMENTO
    # =========================
    for item in rows:
        gid = str(item["global_id"])
        text = str(item["text"])

        # ✅ 1. Classificação avançada
        cls, sub = advanced_classify(text)

        # ✅ 2. fallback
        if not cls:
            cls, sub = smart_fallback(text)

        # ✅ 3. normalização ISO
        final_sub = normalize_to_iso(sub, text)

        # ✅ 4. consistência
        if cls == "FR":
            final_sub = "Functional"

        if cls == "NFR" and final_sub == "Functional":
            cls = "FR"
            final_sub = "Functional"

        output[gid] = (text, cls, final_sub)

    # =========================
    # OUTPUT
    # =========================
    result = []

    for item in rows:
        gid = str(item["global_id"])
        text, cls, sub = output.get(
            gid,
            (str(item["text"]), DEFAULT_CLASS, DEFAULT_SUB),
        )

        conf = compute_confidence(text, cls, sub)

        result.append([
            gid,
            text,
            normalizar_class(cls),
            sub,
            conf
        ])

    return pd.DataFrame(result, columns=OUTPUT_COLUMNS)


