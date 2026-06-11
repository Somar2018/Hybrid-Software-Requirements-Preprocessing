# =========================================================
# utils/metrics.py (FINAL - ISO READY)
# =========================================================

import pandas as pd
import streamlit as st


# =========================================================
# ✅ DETECTAR COLUNA (GENÉRICO)
# =========================================================
def find_column(df, names):
    for c in df.columns:
        if c.lower() in names:
            return c
    return None


# =========================================================
# ✅ MÉTRICAS PRINCIPAIS
# =========================================================
def mostrar_metricas(df):
    """
    Mostra métricas completas (alinhadas com ISO)
    """

    if df is None or df.empty:
        st.warning("⚠️ Dataset vazio")
        return

    df = df.copy()
    df.columns = df.columns.str.strip()

    # detectar colunas
    col_type = find_column(df, ["type"])
    col_sub = find_column(df, ["subclass"])
    col_text = find_column(df, ["text"])
    col_source = find_column(df, ["source", "dataset", "project", "system"])

    st.subheader("📊 Estatísticas Gerais")

    # =====================================================
    # ✅ TOTAL
    # =====================================================
    total = len(df)
    st.write(f"✔ Total de requisitos: {total}")

    # =====================================================
    # ✅ TIPO (FR / NFR)
    # =====================================================
    if col_type:
        type_counts = df[col_type].value_counts()
        type_perc = df[col_type].value_counts(normalize=True) * 100

        st.markdown("### 📌 Tipo de Requisitos")

        for t in type_counts.index:
            st.write(f"{t}: {type_counts[t]} ({type_perc[t]:.1f}%)")

        st.bar_chart(type_counts)

    else:
        st.info("ℹ️ Coluna 'Type' não encontrada")

    # =====================================================
    # ✅ SUBCLASSE ISO 25010
    # =====================================================
    if col_sub:

        st.markdown("### 🧩 Subclasses (ISO 25010)")

        sub_counts = df[col_sub].value_counts()
        sub_perc = df[col_sub].value_counts(normalize=True) * 100

        sub_df = pd.DataFrame({
            "Count": sub_counts,
            "Percent (%)": sub_perc.round(2)
        })

        st.dataframe(sub_df)
        st.bar_chart(sub_counts)

        # ✅ insights automáticos
        st.markdown("### 🧠 Insights ISO")

        expected = [
            "Performance",
            "Usability",
            "Reliability",
            "Security",
            "Maintainability",
            "Compatibility",
            "Portability"
        ]

        missing = [e for e in expected if e not in sub_counts.index]

        if missing:
            st.warning(f"⚠️ Subclasses em falta: {', '.join(missing)}")

        # exemplos úteis
        for key in ["Security", "Performance", "Usability"]:
            if key in sub_counts:
                val = sub_perc[key]
                st.write(f"✔ {key}: {val:.1f}%")

    else:
        st.info("ℹ️ Coluna 'Subclass' não encontrada")

    # =====================================================
    # ✅ DISTRIBUIÇÃO POR DATASET
    # =====================================================
    if col_source:

        st.markdown("### 📊 Distribuição por Dataset")

        if col_type:
            tabela = df.groupby([col_source, col_type]).size().unstack(fill_value=0)
        else:
            tabela = df[col_source].value_counts()

        st.dataframe(tabela)

    # =====================================================
    # ✅ QUALIDADE DO TEXTO
    # =====================================================
    if col_text:

        st.markdown("### 🔍 Qualidade dos Requisitos")

        text_series = df[col_text].astype(str)

        lengths = text_series.apply(len)

        st.write(f"Comprimento médio: {lengths.mean():.1f}")
        st.write(f"Mínimo: {lengths.min()}")
        st.write(f"Máximo: {lengths.max()}")

        short = (lengths < 20).sum()
        long = (lengths > 300).sum()

        st.write(f"⚠️ Muito curtos (<20): {short}")
        st.write(f"⚠️ Muito longos (>300): {long}")

        # ✅ densidade de keywords (interessante para requisitos)
        keywords = ["shall", "must", "should"]

        keyword_hits = text_series.apply(
            lambda x: any(k in x.lower() for k in keywords)
        ).mean() * 100

        st.write(f"📌 Requisitos com palavra-chave típica: {keyword_hits:.1f}%")

    # =====================================================
    # ✅ ANÁLISE AVANÇADA (ISO)
    # =====================================================
    if col_sub and col_text:

        st.markdown("### 🔬 Análise por Subclasse")

        lengths = df[col_text].astype(str).apply(len)

        analysis = df.copy()
        analysis["length"] = lengths

        tabela = analysis.groupby(col_sub).agg({
            "length": ["mean", "min", "max", "count"]
        })

        tabela.columns = ["avg_len", "min_len", "max_len", "count"]

        st.dataframe(tabela)