# ============================================================
#  RLHF – Human Review Detection (versão final ajustada)
# ============================================================

import sys
import os
import pandas as pd

# Root System Path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

# 🔥 Import correto
from pipeline.classify import detect_free_subclass


# ============================================================
# 1. CARREGAR DADOS
# ============================================================

INPUT_FILE = "merged_output.csv"   # <-- ajusta se necessário

df = pd.read_csv(INPUT_FILE)

print("✅ Dados carregados:", len(df))


# ============================================================
# 2. FUNÇÃO RLHF PRINCIPAL
# ============================================================

def needs_human_review(row):

    reasons = []

    texto = str(row["text"]).lower()
    sub = str(row["subclass"])
    cls = str(row["class"])
    conf = float(row["confidence"])

    # ✅ CONFIDENCE (ajustado ao teu dataset real)
    if conf < 0.49:
        reasons.append("low_confidence")

    # ✅ tamanho
    if len(texto) > 300:
        reasons.append("too_long")

    if len(texto) < 20:
        reasons.append("too_short")

    # ✅ não parece requisito
    if not any(k in texto for k in ["shall", "must", "will"]):
        reasons.append("not_clear_requirement")

    flagged = len(reasons) > 0
    return flagged, ", ".join(reasons)

# ============================================================
# 3. APLICAR RLHF
# ============================================================

rlhf_cases = []

for _, row in df.iterrows():

    flagged, reasons = needs_human_review(row)

    if flagged:
        rlhf_cases.append({
        "id": row["id"],
        "text": row["text"],
        "class": row["class"],
        "subclass": row["subclass"],
        "confidence": row["confidence"],   # ✅ IMPORTANTE
        "reasons_rlhf": reasons,
        "comentario": ""
    })


# ============================================================
# 4. GUARDAR RESULTADO
# ============================================================

df_rlhf = pd.DataFrame(rlhf_cases)
df_rlhf.to_csv("rlhf_candidates.csv", index=False)

print("==============================================")
print("✅ RLHF casos detectados:", len(df_rlhf))
#print(df[["text", "confidence"]].head())
print("📄 Guardado em: rlhf_candidates.csv")
print("==============================================")
