import streamlit as st

from utils import load_data_consolidado, load_data_deuda
from datos_generales.render import render_datos_generales
st.set_page_config(
    page_title="Resumen Ejecutivo",
    page_icon="📊",
    layout="wide"
)

if "vista_activa" not in st.session_state:
    st.session_state.vista_activa = "dispersiones"

with st.spinner("Procesando datos financieros..."):
    df = load_data_consolidado()
    df_deuda = load_data_deuda()

if df is not None and not df.empty:
    render_datos_generales(df, df_deuda)