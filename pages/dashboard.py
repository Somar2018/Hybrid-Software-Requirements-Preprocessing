import streamlit as st

st.set_page_config(page_title="Dashboard")

st.title("📊 Dashboard")
st.write("Bem-vindo ao sistema!")

if st.button("Logout"):
    st.session_state.clear()
    st.switch_page("app.py")