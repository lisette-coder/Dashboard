import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURACIÓN Y CARGA DE DATOS DESDE GOOGLE SHEETS
# -----------------------------------------------------------------------------
# ID del documento de Google Sheets
SPREADSHEET_ID = "1YK-uvuptBuRS51Lv6wzOrFR_EmWVmTEDtTU11aRhmr8"

# GIDs correspondientes a cada hoja
GID_CONSOLIDADO = "2069564386"
GID_CAP_DEUDA = "573279847"


@st.cache_data(ttl=1, show_spinner="Cargando reporte consolidado...")
def load_data_consolidado():
    """Lee directamente la pestaña de Reporte Consolidado desde Google Sheets sin límites de filas."""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={GID_CONSOLIDADO}"
    try:
        df = pd.read_csv(url)
        # Limpia espacios innecesarios en los nombres de las columnas
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error al leer la hoja 'Reporte Consolidado': {e}")
        return None


@st.cache_data(ttl=1, show_spinner="Cargando datos de línea de deuda...")
def load_data_deuda():
    """Lee directamente la pestaña 'Cap' (deuda) desde Google Sheets sin límites de filas."""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={GID_CAP_DEUDA}"
    try:
        df_deuda = pd.read_csv(url)
        # Limpia espacios innecesarios en los nombres de las columnas
        df_deuda.columns = df_deuda.columns.str.strip()
        return df_deuda
    except Exception as e:
        st.error(f"Error al leer la hoja de 'Cap / Deuda': {e}")
        return None