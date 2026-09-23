import calendar
from datetime import datetime
import json
import os
from pathlib import Path
import pandas as pd

# ==========================================
# CONFIGURACIÓN DE RUTAS Y PARÁMETROS
# ==========================================
# Ruta del archivo de facturas/deuda (Ajusta la ruta según tu archivo de Excel o CSV)
RUTA_EXCEL_FACTURAS = Path("data/tus_facturas.xlsx")

# Ruta donde se guardará el JSON histórico con los cierres congelados
RUTA_HISTORIAL_JSON = Path("data/historial_mora.json")

# Tasa de interés moratorio mensual (ejemplo: 3.5% mensual)
TASA_INTERES_MENSUAL = 0.035


def cargar_datos_facturas(ruta_archivo):
  """Carga el archivo Excel o CSV de facturas."""
  if not ruta_archivo.exists():
    print(f"❌ Error: El archivo {ruta_archivo} no fue encontrado.")
    return None

  ext = ruta_archivo.suffix.lower()
  if ext in [".xlsx", ".xls"]:
    return pd.read_excel(ruta_archivo)
  elif ext == ".csv":
    return pd.read_csv(ruta_archivo)
  else:
    print(f"❌ Formato no soportado: {ext}")
    return None


def ejecutar_cierre_nocturno_mora():
  """Proceso principal que se ejecuta a las 10:00 PM CST.

  Busca facturas vencidas en 'TO BE PAID' y congela su mora en el JSON.
  """
  hoy = datetime.now()
  periodo_actual = hoy.strftime("%Y-%m")  # Ejemplo: '2026-09'
  fecha_hoy_str = hoy.strftime("%Y-%m-%d")

  print(
      f"🚀 [{fecha_hoy_str} 22:00] Iniciando proceso de cierre nocturno de"
      " mora..."
  )

  # 1. Cargar archivo de facturas
  df = cargar_datos_facturas(RUTA_EXCEL_FACTURAS)
  if df is None or df.empty:
    print("⚠️ No hay datos para procesar.")
    return

  # Limpiar nombres de columnas
  df.columns = df.columns.astype(str).str.strip()

  # 2. Homologar/Validar columnas
  col_venc = "Fecha Vencimiento"
  col_monto = "Monto a Pagar a Kamina"
  col_estatus = "Estatus Pago a Kamina"

  for col in [col_venc, col_monto, col_estatus]:
    if col not in df.columns:
      print(f"❌ Error: La columna '{col}' no existe en el archivo.")
      return

  # Formatear columnas
  df["_Fecha_Venc"] = pd.to_datetime(df[col_venc], errors="coerce")
  df["_Monto"] = pd.to_numeric(df[col_monto], errors="coerce").fillna(0)
  df["_Estatus"] = df[col_estatus].astype(str).str.strip().str.lower()

  # 3. Filtrar facturas que HOY están vencidas y en 'to be paid'
  mask_vencidas = (
      (df["_Fecha_Venc"].dt.date <= hoy.date())
      & (df["_Monto"] > 0)
      & (df["_Estatus"] == "to be paid")
  )

  vencidas = df[mask_vencidas].copy()

  print(f"📊 Facturas vencidas detectadas en TO BE PAID: {len(vencidas)}")

  # 4. Cargar la base de datos JSON existente (o crear una nueva)
  if RUTA_HISTORIAL_JSON.exists():
    with open(RUTA_HISTORIAL_JSON, "r", encoding="utf-8") as f:
      try:
        database = json.load(f)
      except json.JSONDecodeError:
        database = {}
  else:
    database = {}

  # Asegurar la sección del mes actual
  if periodo_actual not in database:
    database[periodo_actual] = {}

  # Cálculo de días del mes y tasa diaria
  dias_en_mes = calendar.monthrange(hoy.year, hoy.month)[1]
  tasa_diaria = TASA_INTERES_MENSUAL / dias_en_mes

  # 5. Iterar y congelar/actualizar registros en el JSON
  registros_actualizados = 0
  for idx, row in vencidas.iterrows():
    # Identificador único de la factura (usa columna ID o genera una combinación única)
    if "ID_Factura" in df.columns and pd.notna(row["ID_Factura"]):
      factura_id = str(row["ID_Factura"]).strip()
    else:
      factura_id = (
          f"FACT_{row['_Fecha_Venc'].strftime('%Y%m%d')}_{int(row['_Monto'])}"
      )

    fecha_venc_date = row["_Fecha_Venc"].date()
    dias_atraso = (hoy.date() - fecha_venc_date).days
    dias_atraso = max(dias_atraso, 1)  # Mínimo 1 día de mora al estar vencida

    interes_mora = row["_Monto"] * tasa_diaria * dias_atraso

    # Guardar en la sección del mes correspondiente
    database[periodo_actual][factura_id] = {
      "Fecha_Vencimiento": fecha_venc_date.strftime("%Y-%m-%d"),
      "Monto_Base": float(row["_Monto"]),
      "Dias_Atraso_Congelados": int(dias_atraso),
      "Interes_Mora_Congelado": round(float(interes_mora), 2),
      "Ultima_Actualizacion": fecha_hoy_str,
    }
    registros_actualizados += 1

  # 6. Guardar los cambios estáticos de vuelta en el archivo JSON
  RUTA_HISTORIAL_JSON.parent.mkdir(parents=True, exist_ok=True)
  with open(RUTA_HISTORIAL_JSON, "w", encoding="utf-8") as f:
    json.dump(database, f, indent=4, ensure_ascii=False)

  print(
      f"✅ Cierre nocturno completado. {registros_actualizados} facturas"
      f" congeladas en el periodo '{periodo_actual}'."
  )


if __name__ == "__main__":
  ejecutar_cierre_nocturno_mora()