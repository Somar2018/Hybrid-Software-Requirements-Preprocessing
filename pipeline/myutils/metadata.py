from pathlib import Path
import pandas as pd


def get_project_name(file):

    filename = Path(file.name).stem.lower()

    mappings = {
        "cps": "Card Payment System",
        "epurse": "Electronic Purse System",
        "e_purse": "Electronic Purse System",
        "epu": "Electronic Purse System"
    }

    for key, value in mappings.items():
        if key in filename:
            return value

    try:
        df = pd.read_csv(file)

        if "text" in df.columns:

            text = " ".join(
                df["text"].astype(str).head(100)
            ).lower()

            if any(k in text for k in ["merchant", "payment", "issuer"]):
                return "Card Payment System"

            if any(k in text for k in ["electronic purse", "wallet", "smart card"]):
                return "Electronic Purse System"

    except Exception:
        pass

    return (
        Path(file.name)
        .stem
        .replace("_", " ")
        .replace("-", " ")
        .title()
    )