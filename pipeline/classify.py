# =========================================================
# CLASSIFICAÇÃO → pipeline/classify.py (REFATORADO)
# =========================================================

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from myutils.text import hybrid_classification
from core.config import build_classification_prompt
from core.llm import perguntar

logger = logging.getLogger(__name__)

# =========================================================
# CONFIG
# =========================================================

VALID_CLASSES = {"FR", "NFR"}

VALID_SUBCLASSES = {
    "Functional",
    "Performance",
    "Usability",
    "Reliability",
    "Security",
    "Maintainability",
    "Compatibility",
    "Portability",
}

DEFAULT_CLASS = "NFR"
DEFAULT_SUB = "Performance"
BATCH_SIZE = 5

# =========================================================
# KEYWORD MAP CENTRALIZADO (MELHOR MANUTENÇÃO)
# =========================================================

KEYWORD_RULES: List[Tuple[Set[str], str, str]] = [
    ({"authenticate", "authentication", "unauthorised", "authorization", "login"}, "NFR", "Security"),
    ({"privacy", "secure", "security", "integrity", "encryption"}, "NFR", "Security"),

    ({"latency", "performance", "throughput", "capacity", "scalability", "delay", "bandwidth"}, "NFR", "Performance"),

    ({"user", "ui", "ux", "interface", "experience", "accessibility"}, "NFR", "Usability"),

    ({"reliable", "availability", "uptime", "fault", "recovery"}, "NFR", "Reliability"),

    ({"maintain", "refactor", "extensible", "modular"}, "NFR", "Maintainability"),
]


# =========================================================
# NORMALIZAÇÃO
# =========================================================

def normalizar_subclasse(sub: Any) -> str:
    if not isinstance(sub, str):
        return DEFAULT_SUB

    sub = sub.strip()

    mapping = {
        "Scalability": "Performance",
        "Availability": "Reliability",
        "Efficiency": "Performance",
        "Performance Efficiency": "Performance",
        "User Experience": "Usability",
    }

    sub = mapping.get(sub, sub)

    return sub if sub in VALID_SUBCLASSES else DEFAULT_SUB


def normalizar_class(cl: str) -> str:
    return cl if cl in VALID_CLASSES else DEFAULT_CLASS


# =========================================================
# HEURÍSTICA MELHORADA
# =========================================================

def heuristic_classify(text: str) -> Optional[Tuple[str, str]]:
    t = text.lower()

    for keywords, cls, sub in KEYWORD_RULES:
        if any(k in t for k in keywords):
            return cls, sub

    return None


# =========================================================
# PARSER ROBUSTO LLM
# =========================================================

def parse_line(line: str, valid_ids: Set[str]) -> Optional[Tuple[str, str, str, str]]:
    if not line:
        return None

    line = line.strip().lstrip("-• ")

    parts = [p.strip() for p in line.split("|")]

    if len(parts) < 3:
        return None

    cid, text, cls = parts[0], parts[1], parts[2]
    sub = parts[3] if len(parts) > 3 else DEFAULT_SUB

    if cid not in valid_ids:
        return None

    cls = normalizar_class(cls)

    if cls == "FR":
        sub = "Functional"
    else:
        sub = normalizar_subclasse(sub)

    return cid, text, cls, sub


# =========================================================
# LLM BATCH
# =========================================================

def classify_batch(
    batch_text: str,
    client: Any,
    model: str,
    provider: str,
    modo: str,
    cache: Optional[Dict[str, str]],
    batch_ids: Set[str],
) -> List[Tuple[str, str, str, str]]:

    try:
        response = perguntar(
            build_classification_prompt(batch_text),
            client,
            model,
            provider,
            modo,
            cache,
        )
    except Exception as e:
        logger.warning("LLM failed: %s", e)
        return []

    results = []

    for line in str(response).splitlines():
        parsed = parse_line(line, batch_ids)
        if parsed:
            results.append(parsed)

    return results


# =========================================================
# FALLBACK INTELIGENTE
# =========================================================

def smart_fallback(text: str) -> Tuple[str, str]:
    t = text.lower()

    for keywords, cls, sub in KEYWORD_RULES:
        if any(k in t for k in keywords):
            return cls, sub

    # fallback conservador melhorado
    # tenta evitar FR falso positivo
    if any(k in t for k in {"system", "must", "shall", "require"}):
        return "NFR", "Maintainability"

    return "FR", "Functional"


# =========================================================
# PIPELINE PRINCIPAL
# =========================================================

def classificar(df: pd.DataFrame, ctx: Dict[str, Any]) -> pd.DataFrame:

    client = ctx["client"]
    model = ctx["model"]
    provider = ctx["provider"]
    modo = ctx["modo"]
    cache = ctx.get("cache")

    rows = df.to_dict("records")
    rows_map = {r["global_id"]: r["text"] for r in rows}

    output: Dict[str, Tuple[str, str, str]] = {}

    for start in range(0, len(rows), BATCH_SIZE):

        batch = rows[start:start + BATCH_SIZE]

        heuristic_batch = []
        llm_batch = []

        # =========================
        # 1. HEURÍSTICA
        # =========================
        for item in batch:
            gid = item["global_id"]
            text = item["text"]

            heur = heuristic_classify(text)

            if heur:
                output[gid] = (text, heur[0], heur[1])
            else:
                llm_batch.append(item)

        # =========================
        # 2. LLM
        # =========================
        if llm_batch:
            llm_ids = {x["global_id"] for x in llm_batch}

            batch_text = "\n".join(
                f"{x['global_id']}|{x['text']}" for x in llm_batch
            )

            llm_results = classify_batch(
                batch_text,
                client,
                model,
                provider,
                modo,
                cache,
                llm_ids,
            )

            parsed_ids = set()

            for cid, text, cls, sub in llm_results:
                output[cid] = (text, cls, sub)
                parsed_ids.add(cid)

            # =========================
            # 3. FALLBACK FINAL
            # =========================
            missing = llm_ids - parsed_ids

            for gid in missing:
                text = rows_map[gid]
                cls, sub = smart_fallback(text)
                output[gid] = (text, cls, sub)

        logger.info(
            "Batch %s processed | heuristic=%s | llm=%s | total=%s",
            start,
            len(batch) - len(llm_batch),
            len(llm_batch),
            len(output),
        )

    return pd.DataFrame(
        [
            [gid, text, cls, sub]
            for gid, (text, cls, sub) in output.items()
        ],
        columns=["global_id", "text", "class", "subclass"],
    )