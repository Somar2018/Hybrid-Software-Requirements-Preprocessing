import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from core.config import PROMPT_EXTRACT
from core.llm import perguntar_extract
from myutils.io import read_file_safe
from myutils.text import (
    limpar,
    limpar_prefixo,
    extrair_requisitos_brutos,
    linha_valida,
)

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 3500
DEFAULT_MAX_WORKERS = 3
DEFAULT_REQUEST_DELAY = 0.2

REQ_PATTERN = r"\b(shall|must|required to|is required to|deve|deverá|é obrigatório|tem de)\b"
GARBAGE_PATTERNS = {"global_id", "text", "type"}
MIN_TEXT_LENGTH = 5
PIPE_DELIMITER = "|"


# =========================================================
# CLEAN OUTPUT
# =========================================================
def clean_llm_output(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"

\[.*?\]

", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# CHUNKING
# =========================================================
def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) + 1 <= max_chars:
            current += " " + sent if current else sent
        else:
            chunks.append(current.strip())
            current = sent
    if current.strip():
        chunks.append(current.strip())
    return chunks


# =========================================================
# PARALELIZAÇÃO
# =========================================================
def parallel_llm_calls(prompts: List[str], ctx: Dict[str, Any],
                       max_workers: int = DEFAULT_MAX_WORKERS,
                       delay: float = DEFAULT_REQUEST_DELAY) -> List[str]:

    if not prompts:
        return []

    def worker(prompt: str) -> str:
        try:
            result = perguntar_extract(prompt, ctx)
            return result if isinstance(result, str) else ""
        except Exception as e:
            logger.warning(f"LLM worker error: {e}")
            return ""

    results = [""] * len(prompts)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(worker, prompt): i
            for i, prompt in enumerate(prompts)
        }
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                results[idx] = future.result(timeout=30)
            except Exception as e:
                logger.warning(f"Future resolution failed: {e}")
                results[idx] = ""
            finally:
                time.sleep(delay)

    return results


# =========================================================
# NORMALIZAÇÃO
# =========================================================
def normalize_requirement_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r'^(?:\d+\s+)*', '', text)
    text = re.sub(r'^(?:OE|CO|UD)-\d+\s*:\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'-\s*$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = limpar(text)
    text = limpar_prefixo(text)
    return text


# =========================================================
# FALLBACK REGEX
# =========================================================
def extrair_regras(texto: str) -> List[str]:
    if not texto or not isinstance(texto, str):
        return []
    linhas = []
    for sent in re.split(r'[.!?]', texto):
        sent = normalize_requirement_text(sent)
        if not sent:
            continue
        if re.search(REQ_PATTERN, sent, re.IGNORECASE) and linha_valida(sent):
            linhas.append(sent)
    return linhas


# =========================================================
# PIPE FORMAT
# =========================================================
def _parse_pipe_format(line: str) -> Optional[Dict[str, str]]:
    parts = [p.strip() for p in line.split(PIPE_DELIMITER)]
    if len(parts) < 3:
        return None
    gid, txt, typ = parts[0], parts[1], parts[2]
    if txt.lower() in GARBAGE_PATTERNS:
        return None
    if len(txt) < MIN_TEXT_LENGTH:
        return None
    return {
        "global_id": gid if gid.lower() != "global_id" else "",
        "text": txt,
        "type": typ if typ else "UNK"
    }


# =========================================================
# DEDUPLICAÇÃO
# =========================================================
def _deduplicate_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    clean = []
    for row in rows:
        key = row.get("text", "").strip()
        if key and key not in seen:
            seen.add(key)
            clean.append(row)
    return clean


# =========================================================
# EXTRAÇÃO PRINCIPAL
# =========================================================
def extrair_com_llm(texto: str, ctx: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    if not texto or not isinstance(texto, str):
        return []

    texto = texto.strip()
    rows = []

    # RAW
    try:
        raw = extrair_requisitos_brutos(texto)
        for t in raw:
            rows.append({"global_id": "", "text": normalize_requirement_text(t), "type": "UNK"})
    except:
        pass

    # LLM
    if ctx:
        try:
            chunks = chunk_text(texto)
            prompts = [c for c in chunks if len(c) > 100]
            respostas = parallel_llm_calls(prompts, ctx)

            extra_prompt = PROMPT_EXTRACT + "\n" + texto
            extra = perguntar_extract(extra_prompt, ctx)
            if extra:
                respostas.append(extra)

            for resp in respostas:
                resp = clean_llm_output(resp)
                for line in resp.splitlines():
                    line = normalize_requirement_text(line)
                    if not linha_valida(line):
                        continue
                    if PIPE_DELIMITER in line:
                        parsed = _parse_pipe_format(line)
                        if parsed:
                            rows.append(parsed)
                        continue
                    if re.search(REQ_PATTERN, line, re.IGNORECASE):
                        rows.append({"global_id": "", "text": line, "type": "UNK"})
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")

    # Fallback regex
    try:
        for t in extrair_regras(texto):
            rows.append({"global_id": "", "text": normalize_requirement_text(t), "type": "UNK"})
    except:
        pass

    clean_rows = _deduplicate_rows(rows)
    return clean_rows


# =========================================================
# PROCESS FILE (FINAL)
# =========================================================
def process_file(file, idx=0, ctx=None):

    if isinstance(file, (str, Path)):
        source_name = Path(file).name
    else:
        source_name = getattr(file, "name", f"uploaded_{idx}")

    print(f"[PROCESS] Lendo arquivo: {source_name}")

    data = read_file_safe(file)

    # -------------------------
    # Caso DataFrame
    # -------------------------
    if isinstance(data, pd.DataFrame):
        df = data.copy()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        rename_map = {
            "requirement_text": "text",
            "requirement": "text",
            "text": "text",
            "class": "type",
            "requirement_id": "global_id",
            "id": "global_id"
        }

        for col in df.columns:
            if col in rename_map:
                df.rename(columns={col: rename_map[col]}, inplace=True)

        # Fallback: tabela falsa
        if "text" not in df.columns:
            print("[PROCESS] DataFrame sem coluna 'text' → fallback LLM")
            text = "\n".join(" ".join(str(x) for x in row if str(x).strip()) for row in df.values)
            rows = extrair_com_llm(text, ctx)
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows)

        if "global_id" not in df.columns:
            df["global_id"] = [f"REQ_{i:05d}" for i in range(len(df))]

        if "type" not in df.columns:
            df["type"] = "UNK"

        df["source"] = source_name
        return df.reset_index(drop=True)

    # -------------------------
    # Caso texto
    # -------------------------
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return pd.DataFrame()

        rows = extrair_com_llm(text, ctx)
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["source"] = source_name

        if "global_id" not in df.columns:
            df["global_id"] = [f"TXT_REQ_{i:05d}" for i in range(len(df))]

        if "type" not in df.columns:
            df["type"] = "UNK"

        return df.reset_index(drop=True)

    return pd.DataFrame()


# =========================================================
# RUN PIPELINE (FINAL)
# =========================================================
def run_pipeline(files: List[Path], ctx: Optional[Dict[str, Any]] = None) -> pd.DataFrame:

    if not files:
        return pd.DataFrame(columns=["global_id", "text", "type", "source"])

    dfs = []

    for idx, file in enumerate(files):
        df = process_file(file, idx, ctx)
        if df is not None and not df.empty:
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=["global_id", "text", "type", "source"])

    return pd.concat(dfs, ignore_index=True)
