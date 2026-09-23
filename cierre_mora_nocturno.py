import calendar
from datetime import datetime
import json
import os
from pathlib import Path
import gdown
import pandas as pd

# ==========================================
# CONFIGURACIÓN DE RUTAS Y PARÁMETROS
# ==========================================
DRIVE_URL = "https://docs.google.com/spreadsheets/d/1NaIOHho98ZpRMfOoyxQFW6HeKvarkUvj/edit?gid=2069564386#gid=2069564386"
TEMP_FILE = "temp_solistica.xlsx"
RUTA_HISTORIAL_JSON = Path("data/historial_mora.json")

# Tasa de interés moratorio mensual (3.5%)
TASA_INTERES_MENSUAL = 0.035


def descargar_excel_drive():
  """Descarga el Excel desde Google Drive."""
  try:
    if "/d/" in DRIVE_URL:
      file_id = DRIVE_URL.split("/d/")[1].split("/")[0]
      download_url = f"https://drive.google.com/uc?id={file_id}"
      print(f"📥 Descargando archivo desde Google Drive...")
      gdown.download(download_url, TEMP_FILE, quiet=True)
      return TEMP_FILE
  except Exception as e:
    print(f"❌ Error al descargar desde Google Drive: {e}")
    return None


def cargar_datos_reporte_consolidado():
  """Descarga el Excel y lee la pestaña 'Reporte Consolidado'."""
  archivo = descargar_excel_drive()
  if archivo and os.path.exists(archivo):
    try:
      df = pd.read_excel(archivo, sheet_name="Reporte Consolidado")
      return df
    except Exception as e:
      print(f"❌ Error al leer la pestaña 'Reporte Consolidado': {e}")
      return None
  return None


def ejecutar_cierre_nocturno_mora():
  """Proceso de congelamiento a las 10:00 PM CST."""
  hoy = datetime.now()
  periodo_actual = hoy.strftime("%Y-%m")
  fecha_hoy_str = hoy.strftime("%Y-%m-%d")

  print(
      f"🚀 [{fecha_hoy_str} 22:00] Iniciando proceso de cierre nocturno de"
      " mora..."
  )

  # 1. Cargar la pestaña 'Reporte Consolidado'
  df = cargar_datos_reporte_consolidado()

  # Limpiar archivo temporal
  if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)

  if df is None or df.empty:
    print("⚠️ No se obtuvieron datos.")
    return

  # Normalizar nombres de columnas
  df.columns = df.columns.astype(str).str.strip()

  # 2. Definición exacta de tus columnas
  col_venc = "Fecha de Vencimiento"
  col_monto = "Monto a Pagar a Kamina"
  col_estatus = "Estatus Pago a Kamina"

  for col in [col_venc, col_monto, col_estatus]:
    if col not in df.columns:
      print(
          f"❌ Error: La columna '{col}' no existe en 'Reporte Consolidado'."
      )
      return

  # Formatear datos
  df["_Fecha_Venc"] = pd.to_datetime(df[col_venc], errors="coerce")
  df["_Monto"] = pd.to_numeric(df[col_monto], errors="coerce").fillna(0)
  df["_Estatus"] = df[col_estatus].astype(str).str.strip().str.lower()

  # 3. Regla: Estatus "To be paid" y Vencimiento menor a la fecha actual (10:00 PM)
  mask_vencidas = (
      (df["_Fecha_Venc"].dt.date <= hoy.date())
      & (df["_Monto"] > 0)
      & (df["_Estatus"] == "to be paid")
  )

  vencidas = df[mask_vencidas].copy()

  print(
      f"📊 Facturas vencidas encontradas ('To be paid'): {len(vencidas)}"
  )

  # 4. Cargar/inicializar base de datos JSON
  if RUTA_HISTORIAL_JSON.exists():
    with open(RUTA_HISTORIAL_JSON, "r", encoding="utf-8") as f:
      try:
        database = json.load(f)
      except json.JSONDecodeError:
        database = {}
  else:
    database = {}

  if periodo_actual not in database:
    database[periodo_actual] = {}

  # Días reales del mes activo para el prorrateo de la tasa diaria
  dias_en_mes = calendar.monthrange(hoy.year, hoy.month)[1]
  tasa_diaria = TASA_INTERES_MENSUAL / dias_en_mes

  # 5. Guardar/Congelar facturas vencidas en el JSON
  registros_actualizados = 0
  for idx, row in vencidas.iterrows():
    # ID único combinando fecha y monto
    factura_id = (
        f"FACT_{row['_Fecha_Venc'].strftime('%Y%m%d')}_{int(row['_Monto'])}"
    )

    fecha_venc_date = row["_Fecha_Venc"].date()
    dias_atraso = (hoy.date() - fecha_venc_date).days
    dias_atraso = max(dias_atraso, 1)

    interes_mora = row["_Monto"] * tasa_diaria * dias_atraso

    database[periodo_actual][factura_id] = {
        "Fecha_Vencimiento": fecha_venc_date.strftime("%Y-%m-%d"),
        "Monto_Base": float(row["_Monto"]),
        "Dias_Atraso_Congelados": int(dias_atraso),
        "Interes_Mora_Congelado": round(float(interes_mora), 2),
        "Ultima_Actualizacion": fecha_hoy_str,
    }
    registros_actualizados += 1

  # 6. Escribir cambios estáticos en disco
  RUTA_HISTORIAL_JSON.parent.mkdir(parents=True, exist_ok=True)
  with open(RUTA_HISTORIAL_JSON, "w", encoding="utf-8") as f:
    json.dump(database, f, indent=4, ensure_ascii=False)

  print(
      f"✅ Cierre nocturno completado. {registros_actualizados} facturas"
      f" congeladas en el periodo '{periodo_actual}'."
  )


if __name__ == "__main__":
  ejecutar_cierre_nocturno_mora()