# ============================================================
# myutils/cleaner.py
# ============================================================

import re


def clean_requirement_text(text: str) -> str:
    """
    Limpa artefactos de CSV, exportações anteriores do pipeline
    e caracteres indesejados dos requisitos.
    """

    if text is None:
        return ""

    text = str(text)

    # BOM UTF-8
    text = text.replace("ï»¿", "")

    # remover aspas simples e múltiplas
    text = text.replace('"', "")

    # remover espaços no início/fim
    text = text.strip()

    # remover header exportado
    if re.match(
        r'^\s*,?\s*id\s*,\s*text\s*,\s*class\s*,\s*subclass\s*,\s*confidence',
        text,
        flags=re.I,
    ):
        return ""

    # remover:
    # 61,F0_REQ_00061,
    text = re.sub(
        r'^\d+\s*,\s*F\d+_REQ_\d+\s*,',
        '',
        text,
        flags=re.I,
    )

    # remover:
    # F0_REQ_00061,
    text = re.sub(
        r'^F\d+_REQ_\d+\s*,',
        '',
        text,
        flags=re.I,
    )

    # remover:
    # ,FR,Functional,0.8
    # ,NFR,Security,0.9
    text = re.sub(
        r',\s*(FR|NFR)\s*,\s*[^,]+\s*,\s*\d+(\.\d+)?\s*$',
        '',
        text,
        flags=re.I,
    )

    # remover linhas vazias e lixo residual
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")

    # espaços múltiplos
    text = re.sub(r"\s+", " ", text)

    # remover vírgulas repetidas
    text = re.sub(r",\s*,+", ", ", text)

    return text.strip()