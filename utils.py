import io
from datetime import datetime
import gdown
import pandas as pd
import plotly.express as px
import streamlit as st
import os
from pathlib import Path
import json


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


RUTA_HISTORIAL_JSON = Path("data/historial_mora.json")


def obtener_mora_congelada_consolidada():
  """Lee el JSON congelado por GitHub Actions y devuelve únicamente

  el ÚLTIMO cierre registrado para evitar duplicación de periodos.
  """
  if not RUTA_HISTORIAL_JSON.exists():
    return pd.DataFrame()

  try:
    with open(RUTA_HISTORIAL_JSON, "r", encoding="utf-8") as f:
      database = json.load(f)

    if not database:
      return pd.DataFrame()

    # Tomar el último período ejecutado (la clave de fecha más reciente)
    ultimos_periodos = sorted(database.keys())
    if not ultimos_periodos:
      return pd.DataFrame()

    ultimo_cierre = ultimos_periodos[-1]  # P. ej. "2026-09-23"
    facturas_ultimo_cierre = database[ultimo_cierre]

    registros = []
    for f_id, info in facturas_ultimo_cierre.items():
      copia = info.copy()
      copia["Periodo_Cierre"] = ultimo_cierre
      copia["Factura_ID"] = f_id
      registros.append(copia)

    return pd.DataFrame(registros)
  except Exception as e:
    st.error(f"Error al leer el historial de mora congelado: {e}")
    return pd.DataFrame()