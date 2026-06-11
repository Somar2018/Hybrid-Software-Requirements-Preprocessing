import json
from typing import Dict, List, Any

import pandas as pd
from core.llm import perguntar_extract
from myutils.io import read_file_safe
from myutils.text import limpar, hybrid_classification

from core.config import (
    build_extract_prompt,
    build_classification_prompt,
    VALID_REQUIREMENT_TYPES,
    VALID_SUBCLASSES,
    DEFAULT_REQUIREMENT_TYPE,
    DEFAULT_SUBCLASS,
)

def extract_text(path):
    conteudo = read_file_safe(path)
    ...
    return conteudo

# =========================================================
# 🔹 LLM CALL
# =========================================================
def _call_llm(prompt: str, ctx: Dict[str, Any]) -> str:
    client = ctx.get("client")
    model = ctx.get("model")

    if not client or not model:
        print("[LLM] client/model não configurados")
        return ""

    try:
        resp = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

        if hasattr(resp, "choices"):
            return resp.choices[0].message.content

        return str(resp)

    except Exception as e:
        print("[LLM] erro:", e)
        return ""

def extrair_com_llm(text: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not text.strip():
        return []

    # ✅ usar o sistema correto
    resp = perguntar_extract(text, ctx)

    print("LLM OUTPUT:", resp[:300])

    rows = _parse_pipe(resp)

    if not rows:
        rows = [
            {"global_id": None, "text": l.strip(), "type": "UNK"}
            for l in resp.split("\n")
            if len(l.strip()) > 30
        ]

    return rows

def split_text(text: str, max_lines: int = 12) -> list:
    lines = text.split("\n")

    chunks = []
    current = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        current.append(line)

        if len(current) >= max_lines:
            chunks.append("\n".join(current))
            current = []

    if current:
        chunks.append("\n".join(current))

    return chunks

import re

def split_long_requirement(text: str) -> List[str]:
    if not text:
        return []

    # separadores mais seguros
    parts = re.split(
        r"(?:\.\s+(?=[A-Z])|;\s+|\n|\bin addition\b|\band\b)",
        text
    )

    cleaned = []

    for p in parts:
        p = p.strip()

        if len(p) < 25:
            continue

        if not ("shall" in p.lower() or "must" in p.lower()):
            continue

        cleaned.append(p)

    return cleaned if cleaned else [text]

# =========================================================
# 🔹 PARSER
# =========================================================
def _parse_pipe(text: str) -> List[Dict[str, Any]]:
    rows = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = [p.strip() for p in line.split("|")]

        if len(parts) >= 2:
            rows.append({
                "global_id": parts[0] if parts[0].startswith("REQ") else None,
                "text": parts[1],
                "type": parts[2] if len(parts) > 2 else "UNK"
            })
        elif len(line) > 25:
            rows.append({
                "global_id": None,
                "text": line,
                "type": "UNK"
            })

    return rows

def generate_semantic_id(text: str, idx: int) -> str:
    t = text.lower()

    if "voice" in t:
        domain = "VOICE"
    elif "data" in t:
        domain = "DATA"
    elif "call" in t:
        domain = "CALL"
    elif "network" in t:
        domain = "NET"
    elif "emergency" in t:
        domain = "EMERG"
    else:
        domain = "GEN"

    if "priority" in t:
        sub = "PRIO"
    elif "group" in t:
        sub = "GROUP"
    elif "broadcast" in t:
        sub = "BCAST"
    elif "point-to-point" in t:
        sub = "P2P"
    else:
        sub = "GEN"

    return f"FR_{domain}_{sub}_{idx:04d}"

def quality_filter(rows):
    good = []

    for r in rows:
        t = r["text"]

        if len(t) < 20:
            continue

        if t.count("shall") > 3:
            continue

        if not t.endswith("."):
            t += "."

        r["text"] = t
        good.append(r)

    return good

def deduplicate(rows):
    seen = set()
    unique = []

    for r in rows:
        key = re.sub(r"\W+", "", r["text"].lower())

        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique

# =========================================================
# 🔹 CLEAN NOISE
# =========================================================
def is_noise(text: str) -> bool:

    if not text:
        return True

    t = text.lower().strip()

    if len(t) < 8:
        return True

    # ✅ só remover casos óbvios
    if t in ["date", "version"]:
        return True

    return False

def keep_relevant_text(text: str) -> str:
    lines = text.split("\n")

    filtered = [
        l for l in lines
        if any(k in l.lower() for k in [
            "shall", "must", "create", "manage",
            "define", "track", "allow", "provide"
        ])
        or len(l.strip()) > 60   # ✅ mantém frases longas
    ]

    return "\n".join(filtered)


# ✅ COLOCA AQUI (logo abaixo)

def is_real_requirement(text: str) -> bool:
    if not text:
        return False

    t = text.lower().strip()

    if len(t) < 30:
        return False

    # ✅ tem verbo obrigatório
    if not any(k in t for k in ["shall", "must", "should"]):
        return False

    # ✅ lixo típico
    if any(k in t for k in [
        "table of contents",
        "document history",
        "figure",
        "annex"
    ]):
        return False

    return True

def normalize_requirement(text: str) -> str:
    import re

    t = text.strip()

    # remover numeração tipo 9.2.3
    t = re.sub(r"^\d+(\.\d+)*\s*", "", t)

    # remover hífens iniciais
    t = re.sub(r"^[\-\•]\s*", "", t)

    # corrigir duplicações
    t = re.sub(r"(the system shall\s*)+", "The system shall ", t, flags=re.I)

    # forçar "shall"
    if "shall" not in t.lower():
        t = f"The system shall {t}"

    # garantir ponto final
    if not t.endswith("."):
        t += "."

    # capitalizar
    return t[0].upper() + t[1:]

# =========================================================
# 🔹 CLASSIFICAÇÃO
# =========================================================
def _classify_rules(rows):
    for r in rows:
        t = r["text"].lower()

        if "shall" in t:
            r["type"] = "FR"
        elif any(k in t for k in ["performance", "latency", "%", "time"]):
            r["type"] = "NFR"

        # subclass
        if "voice" in t:
            r["subclass"] = "VOICE"
        elif "data" in t:
            r["subclass"] = "DATA"
        elif "security" in t:
            r["subclass"] = "SECURITY"
        elif "performance" in t:
            r["subclass"] = "PERFORMANCE"
        else:
            r["subclass"] = "GEN"

def _classify_with_llm(rows, ctx):
    # versão simples (opcional)
    return

def _ensure_ids(rows):
    for i, r in enumerate(rows, 1):
        if not r.get("global_id"):
            r["global_id"] = generate_semantic_id(r["text"], i)
    for i, r in enumerate(rows, 1):
        if not r.get("global_id"):
            r["global_id"] = generate_semantic_id(r["text"], i)



# =========================================================
# 🔹 PROCESSAMENTO PRINCIPAL
# =========================================================
def process_file(file, idx: int, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:

    print(f"[PROCESS] Arquivo {idx+1}: {getattr(file, 'name', '')}")

    content = read_file_safe(file)

    if content is None:
        print("⚠️ Conteúdo inválido")
        return []

    print("\n=== SAMPLE INPUT ===")
    print(str(content)[:800])
    print("====================\n")

    # ✅ converter DataFrame para texto
    if isinstance(content, pd.DataFrame):
        content = "\n".join(
            content.astype(str).fillna("").agg(" ".join, axis=1)
        )

    # -------- TEXT ----------
    if isinstance(content, str):

        # ✅ remover lixo inicial (TOC / capa)
        #content = content[2000:]

        # ✅ manter só conteúdo relevante
        content = keep_relevant_text(content)

        chunks = split_text(content)

        rows = []

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}")

            chunk_rows = extrair_com_llm(chunk, ctx)

            if chunk_rows:
                rows.extend(chunk_rows)

        print("LLM rows:", len(rows))

        # ✅ fallback
        if not rows:
            rows = [
                {"global_id": None, "text": l.strip(), "type": "UNK", "subclass": None}
                for l in content.split("\n")
                if len(l.strip()) > 30
            ]

        # ✅ limpar texto
        for r in rows:
            r["text"] = limpar(r.get("text", ""))

        # ✅ SPLIT PRIMEIRO (🔥 importante)
        expanded_rows = []

        for r in rows:
            text = r["text"]

            # ✅ só dividir se for MUITO longo
            if len(text) > 200:
                parts = split_long_requirement(text)
            else:
                parts = [text]

            for p in parts:
                expanded_rows.append({
                    "global_id": None,
                    "text": p,
                    "type": r.get("type", "UNK"),
                    "subclass": None
                })

        # ✅ remover lixo
        rows = [r for r in rows if not is_noise(r["text"])]

        # ✅ filtro semântico
        filtered = [r for r in rows if is_real_requirement(r["text"])]

        if filtered:
            rows = filtered
        
        print("DEBUG rows final:", len(rows))

        if not rows:
            return []

        # ✅ normalização
        for r in rows:
            r["text"] = normalize_requirement(r["text"])

        # ✅ remover duplicados
        rows = deduplicate(rows)

        # ✅ FILTRO DE QUALIDADE (✅ AQUI)
        rows = quality_filter(rows)

        # ✅ IDs semânticos (depois de limpar!)
        _ensure_ids(rows)

        # ✅ classificação
        _classify_rules(rows)

    # -------- fallback ----------
    if isinstance(content, str):
        ...
        return rows

    else:
        print("[PROCESS] Conteúdo não suportado")
        return []

# =========================================================
# 🔹 PIPELINE
# =========================================================
def run_pipeline(files, ctx):

    all_rows = []

    for i, f in enumerate(files):
        rows = process_file(f, i, ctx)

        # ✅ proteção contra None
        if rows:
            all_rows.extend(rows)

    # ✅ se vazio
    if not all_rows:
        return pd.DataFrame(columns=["global_id", "text", "type", "subclass"])

    # ✅ 1. criar DataFrame PRIMEIRO
    df = pd.DataFrame(all_rows)

    # ✅ 2. garantir colunas
    if "global_id" not in df.columns:
        df["global_id"] = None

    if "text" not in df.columns:
        df["text"] = ""

    if "type" not in df.columns:
        df["type"] = "UNK"

    if "subclass" not in df.columns:
        df["subclass"] = None

    # ✅ 3. retornar ordenado
    return df[["global_id", "text", "type", "subclass"]]

def is_valid_requirement(text):
    if not text:
        return False

    t = text.strip().lower()

    # ✅ muito longo → lixo
    if len(t) > 220:
        return False

    # ✅ precisa de verbo real
    if not any(k in t for k in ["shall", "must", "should"]):
        return False

    # ✅ múltiplos pontos = bloco
    if t.count(".") > 2:
        return False

    # ✅ lixo típico
    if any(k in t for k in [
        "introduction",
        "this section",
        "table",
        "definition",
        "figure"
    ]):
        return False

    return True
