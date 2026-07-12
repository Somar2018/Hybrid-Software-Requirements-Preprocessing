import pandas as pd


import os

folder = G:\Preprocessing\Dataset-SecReq\CPN.csv

print("📂 Conteúdo da pasta:")
print(os.listdir(folder))


df_raw = None  # garantir que existe

# Detectar tipo de ficheiro
if file_path.endswith(".csv"):
    encodings = ["utf-8", "cp1252", "latin1"]
    for enc in encodings:
        try:
            df_raw = pd.read_csv(file_path, header=None, encoding=enc)
            print(f"✅ CSV lido com encoding: {enc}")
            break
        except Exception as e:
            print(f"Erro com encoding {enc}: {e}")

elif file_path.endswith(".xlsx"):
    df_raw = pd.read_excel(file_path, header=None, engine="openpyxl")
    print("✅ Excel lido com sucesso")

# ✅ verificação CRÍTICA
if df_raw is None:
    raise ValueError("Erro: ficheiro não foi carregado corretamente!")

# processar linhas
lines = df_raw.astype(str).agg(" ".join, axis=1)

data = []

for line in lines:
    if ";" in line:
        parts = line.split(";")
        req = parts[0].strip().replace('"', '')
        cls = parts[-1].strip()
        data.append([req, cls])

df = pd.DataFrame(data, columns=["Requirement text", "Class"])

df.to_excel("output.xlsx", index=False)

print("✅ Ficheiro convertido com sucesso!")
