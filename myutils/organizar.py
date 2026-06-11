# =========================================================
# ORGANIZAÇÃO DE DADOS → utils/organizar.py ✅ FINAL CLEAN
# =========================================================

import re

def organizar(df, dataset_id="D1"):

    if df is None or df.empty:
        return df

    df = df.copy()

    # -----------------------------------------------------
    # ✅ NORMALIZAR NOMES DE COLUNAS
    # -----------------------------------------------------
    df.columns = [
        str(c).strip().lower().replace(" ", "_")
        for c in df.columns
    ]

    # -----------------------------------------------------
    # ✅ MAPEAMENTO INTELIGENTE
    # -----------------------------------------------------
    col_map = {
        "description": "text",
        "requirement_text": "text",
        "req_text": "text",
        "sentence": "text"
    }

    for col in df.columns:
        if col in col_map:
            df.rename(columns={col: col_map[col]}, inplace=True)

    # -----------------------------------------------------
    # ✅ GARANTIR COLUNA TEXT
    # -----------------------------------------------------
    if "text" not in df.columns:
        df["text"] = ""

    df["text"] = df["text"].astype(str)

    # -----------------------------------------------------
    # ✅ LIMPEZA FINAL DO TEXTO (FORTE)
    # -----------------------------------------------------
    df["text"] = df["text"].str.strip()

    # remover "Text:" / "Texto limpo:"
    df["text"] = df["text"].str.replace(
        r'^(Text:|Texto limpo:)\s*',
        '',
        regex=True,
        case=False
    )

    # remover aspas múltiplas
    df["text"] = df["text"].str.replace(r'"+', '', regex=True)

    # remover numeração tipo 2.6.3.5
    df["text"] = df["text"].str.replace(r'^\d+(\.\d+)+\s*', '', regex=True)

    # remover placeholders [xxx]
    df["text"] = df["text"].str.replace(r'\[.*?\]', '', regex=True)

    # normalizar espaços
    df["text"] = df["text"].str.replace(r'\s+', ' ', regex=True)

    # -----------------------------------------------------
    # ✅ FILTRO DE QUALIDADE
    # -----------------------------------------------------
    df = df[df["text"].str.len() > 15]
    df = df[df["text"].str.split().str.len() >= 5]

    # opcional: manter apenas frases completas
    df = df[df["text"].str.endswith(".")]

    # -----------------------------------------------------
    # ✅ SOURCE → PROJECT_ID
    # -----------------------------------------------------
    if "source" not in df.columns:
        df["source"] = "unknown"

    df["project_id"] = df["source"].astype(str).str.strip()

    # -----------------------------------------------------
    # ✅ DATASET ID
    # -----------------------------------------------------
    df["dataset_id"] = dataset_id

    # -----------------------------------------------------
    # ✅ SELEÇÃO FINAL (APENAS 3 COLUNAS)
    # -----------------------------------------------------
    df_final = df[
        ["dataset_id", "project_id", "text"]
    ].rename(columns={
        "text": "requirement_text"
    })

    # -----------------------------------------------------
    # ✅ REMOVER DUPLICADOS
    # -----------------------------------------------------
    df_final = df_final.drop_duplicates(subset=["requirement_text"])

    df_final = df_final.reset_index(drop=True)

    return df_final