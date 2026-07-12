import pandas as pd

input_file = r"G:\Preprocessing\Dataset-SecReq\ePurse-selective.csv"

print(f"📄 Ficheiro de entrada: {input_file}")

try:
    df = pd.read_csv(
        input_file,
        encoding='utf-8',
        encoding_errors='replace',
        header=None
    )
    print("✅ Ficheiro carregado com UTF-8")

except Exception as e:
    print(f"⚠️ UTF-8 falhou: {e}")
    
    try:
        df = pd.read_csv(
            input_file,
            encoding='latin-1',
            header=None
        )
        print("✅ Ficheiro carregado com latin-1")

    except Exception as e2:
        raise Exception(f"❌ Falha total na leitura: {e2}")

# =========================
# LIMPEZA
# =========================

# remover espaços
df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

# remover linhas vazias
df = df.dropna(how='all')

# normalizar espaços
df = df.replace(r'\s+', ' ', regex=True)

# remover caracteres estranhos
df = df.replace(r'[^\x00-\x7F]+', '', regex=True)

df = df.reset_index(drop=True)

print("🧹 Limpeza concluída")

# =========================
# GUARDAR
# =========================

output_file = r"G:\Preprocessing\Dataset-SecReq\ePurse-clean.csv"

df.to_csv(output_file, index=False, header=False, encoding='utf-8')

print(f"💾 Guardado em: {output_file}")
print(f"📊 Linhas: {df.shape[0]} | Colunas: {df.shape[1]}")