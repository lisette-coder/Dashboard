import io
from datetime import datetime
import gdown
import pandas as pd
import plotly.express as px
import streamlit as st
import os
from pathlib import Path


# URL constante de Google Drive
DRIVE_URL = "https://docs.google.com/spreadsheets/d/1NaIOHho98ZpRMfOoyxQFW6HeKvarkUvj/edit?gid=2069564386#gid=2069564386"
OUTPUT_FILE = "temp_solistica.xlsx"

# Función interna de apoyo para descargar una sola vez
@st.cache_data(ttl=1800, show_spinner="Cargando reporte consolidado...")
def _download_drive_file():
    try:
        if "/d/" in DRIVE_URL:
            file_id = DRIVE_URL.split("/d/")[1].split("/")[0]
            download_url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(download_url, OUTPUT_FILE, quiet=True)
            return OUTPUT_FILE
    except Exception as e:
        st.error(f"Error al conectar con Google Drive: {e}")
        return None

# Mantiene exactamente el nombre y comportamiento de tus variables/funciones
@st.cache_data(ttl=1800, show_spinner="Cargando reporte consolidado...")
def load_data_consolidado():
    archivo = _download_drive_file()
    if archivo and os.path.exists(archivo):
        try:
            df = pd.read_excel(archivo, sheet_name="Reporte Consolidado")
            return df
        except Exception as e:
            st.error(f"Error al leer pestaña 'Reporte Consolidado': {e}")
            return None
    return None

@st.cache_data(ttl=60, show_spinner="Cargando reporte consolidado...")
def load_data_deuda():
    archivo = _download_drive_file()
    if archivo and os.path.exists(archivo):
        try:
            df_deuda = pd.read_excel(archivo, sheet_name="Cap")
            return df_deuda
        except Exception as e:
            st.error(f"Error al leer pestaña 'Cap': {e}")
            return None
    return None
