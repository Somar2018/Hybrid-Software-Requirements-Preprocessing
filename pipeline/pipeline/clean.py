import re
import pandas as pd


def clean_text(text):

    if pd.isna(text):
        return text

    text = str(text)

    # remover todas as aspas
    text = text.replace('"', '')

    # remover apóstrofos repetidos
    text = re.sub(r"'{2,}", "", text)

    # remover tabs e quebras de linha
    text = re.sub(r'[\r\n\t]+', ' ', text)

    # remover caracteres de controlo
    text = re.sub(r'[\x00-\x1F\x7F]+', '', text)

    # remover espaços repetidos
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def clean_dataframe(df):

    if df is None:
        return pd.DataFrame()

    if df.empty:
        return df

    df = df.copy()

    # remover linhas vazias
    df = df.dropna(how="all")

    # limpar todas as colunas texto
    for col in df.columns:

        if df[col].dtype == "object":

            df[col] = (
                df[col]
                .astype(str)
                .apply(clean_text)
            )

    # nomes possíveis da coluna de requisito
    requirement_columns = [
        "Requirement Text",
        "requirement_text",
        "text",
        "requirement"
    ]

    for col in requirement_columns:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype(str)
                .apply(clean_text)
            )

            # remover requisitos vazios
            df = df[
                df[col]
                .str.strip()
                .str.len() > 3
            ]

    # remover duplicados
    df = df.drop_duplicates()

    # reset index
    df = df.reset_index(drop=True)

    return df


def run_pipeline(files):

    dfs = []

    for file in files:

        file.seek(0)

        try:

            df = pd.read_csv(
                file,
                encoding="utf-8",
                encoding_errors="replace",
                on_bad_lines="skip"
            )

        except Exception:

            try:

                file.seek(0)

                df = pd.read_csv(
                    file,
                    encoding="latin-1",
                    on_bad_lines="skip"
                )

            except Exception as e:

                print(
                    f"Erro ao ler {file.name}: {e}"
                )

                continue

        print(
            f"ANTES LIMPEZA: {file.name} -> {df.shape}"
        )

        df = clean_dataframe(df)

        print(
            f"DEPOIS LIMPEZA: {file.name} -> {df.shape}"
        )

        if not df.empty:
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    final_df = pd.concat(
        dfs,
        ignore_index=True
    )

    final_df = final_df.reset_index(
        drop=True
    )

    return final_df