import streamlit as st
from aml_dashboard import render_aml_tab

st.set_page_config(page_title="AML Alert Re-ranker", layout="wide", page_icon="🔍")
st.title("🔍 AML Alert Re-ranker")
render_aml_tab()
