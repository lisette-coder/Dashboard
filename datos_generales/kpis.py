import pandas as pd
import streamlit as st
from datetime import datetime

from .callbacks import cambiar_vista
from .constantes import NOMBRES_MESES


def _limpiar_a_float(val):
    """Auxiliar para limpiar valores con '$', '%', ',' y convertirlos a float de forma segura."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = (
        str(val).replace("$", "").replace(",", "").replace("%", "").strip()
    )
    return pd.to_numeric(val_str, errors="coerce") or 0.0


def render_kpis(df, df_deuda=None):
    st.markdown("### 📊 Indicadores Clave de Rendimiento")

    # Preparación de fechas para el filtro superior
    df_copia = df.copy()
    if "Fecha de Dispersión" in df_copia.columns:
        df_copia["_Fecha_Temp"] = pd.to_datetime(
            df_copia["Fecha de Dispersión"], errors="coerce"
        )
        df_copia["_Anio"] = df_copia["_Fecha_Temp"].dt.year
        df_copia["_Mes"] = df_copia["_Fecha_Temp"].dt.month
    else:
        df_copia["_Anio"] = datetime.now().year
        df_copia["_Mes"] = datetime.now().month

    anios_disponibles = sorted(df_copia["_Anio"].dropna().unique())
    if not anios_disponibles:
        anios_disponibles = [datetime.now().year]

    col_kpi_filt1, col_kpi_filt2, _ = st.columns([1, 1, 2])

    with col_kpi_filt1:
        anio_kpi = st.selectbox(
            "Año KPI",
            anios_disponibles,
            index=len(anios_disponibles) - 1,
            key="kpi_anio_filter",
        )

    meses_disponibles = sorted(
        df_copia[df_copia["_Anio"] == anio_kpi]["_Mes"].dropna().unique()
    )
    if not meses_disponibles:
        meses_disponibles = list(NOMBRES_MESES.keys())

    # Seleccionar por defecto el mes actual o el último mes disponible
    mes_actual_idx = datetime.now().month
    default_mes_idx = (
        meses_disponibles.index(mes_actual_idx)
        if mes_actual_idx in meses_disponibles
        else len(meses_disponibles) - 1
    )

    with col_kpi_filt2:
        mes_kpi = st.selectbox(
            "Filtrar Tarjetas por Mes",
            meses_disponibles,
            index=default_mes_idx,
            format_func=lambda x: NOMBRES_MESES.get(x, f"Mes {x}"),
            key="kpi_mes_filter",
        )

    # Filtrar dataframes YTD (Año actual seleccionado) y Mes (Año y Mes seleccionados)
    df_ytd = df_copia[df_copia["_Anio"] == anio_kpi].copy()
    df_mes_actual = df_copia[
        (df_copia["_Anio"] == anio_kpi) & (df_copia["_Mes"] == mes_kpi)
    ].copy()
    nombre_mes_sel = NOMBRES_MESES.get(mes_kpi, "Mes sel.")

    # KPIS PRINCIPALES
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    # --- TARJETA 1: Monto Total de Dispersiones ---
    monto_mes_actual = 0.0
    monto_dia_anterior = 0.0

    if "Monto Dispersado" in df_copia.columns and "_Fecha_Temp" in df_copia.columns:
        df_copia["Monto Dispersado_Num"] = df_copia["Monto Dispersado"].apply(_limpiar_a_float)
        df_mes_actual["Monto Dispersado_Num"] = df_mes_actual["Monto Dispersado"].apply(_limpiar_a_float)

        hoy = datetime.now().date()

        if anio_kpi == hoy.year and mes_kpi == hoy.month:
            df_hasta_hoy = df_mes_actual[
                df_mes_actual["_Fecha_Temp"].dt.date <= hoy
            ]
            monto_mes_actual = df_hasta_hoy["Monto Dispersado_Num"].sum()

            fecha_ayer = hoy - pd.Timedelta(days=1)
            monto_dia_anterior = df_mes_actual[
                df_mes_actual["_Fecha_Temp"].dt.date == fecha_ayer
            ]["Monto Dispersado_Num"].sum()
        else:
            monto_mes_actual = df_mes_actual["Monto Dispersado_Num"].sum()
            if not df_mes_actual.empty:
                ultima_fecha_mes = df_mes_actual["_Fecha_Temp"].dt.date.max()
                monto_dia_anterior = df_mes_actual[
                    df_mes_actual["_Fecha_Temp"].dt.date == ultima_fecha_mes
                ]["Monto Dispersado_Num"].sum()

        col1.metric(
            label=f"Dispersiones ({nombre_mes_sel} {anio_kpi})",
            value=f"${monto_mes_actual:,.2f}",
            delta=f"Día anterior: ${monto_dia_anterior:,.2f}",
            delta_color="off",
        )
    else:
        col1.metric(label="Dispersiones", value="Columna no encontrada")

    col1.button(
        "Ver más",
        key="btn_disp",
        on_click=cambiar_vista,
        args=("dispersiones",),
    )

    # --- TARJETA 2: Cartera De clientes ---
    pago_kamina_col = "Monto a Pagar a Kamina"
    estatus_pago_col = "Estatus Pago a Kamina"
    col_fecha_pago = "Fecha Vencimiento"

    if estatus_pago_col in df.columns and col_fecha_pago in df.columns:
        df_copia_cartera = df.copy()
        
        # Limpieza de estatus y montos
        df_copia_cartera[estatus_pago_col] = (
            df_copia_cartera[estatus_pago_col].astype(str).str.strip()
        )
        df_copia_cartera[pago_kamina_col] = df_copia_cartera[pago_kamina_col].apply(_limpiar_a_float)

        # 1. Filtrar solo 'To be paid'
        df_cartera = df_copia_cartera[
            df_copia_cartera[estatus_pago_col] == "To be paid"
        ]
        total_cartera = df_cartera[pago_kamina_col].sum()

        total_acumulado_hasta_hoy = 0.0
        if not df_cartera.empty:
            hoy = datetime.now().date()

            # 2. Parsear fechas considerando que el día va primero (dayfirst=True)
            fechas_convertidas = pd.to_datetime(
                df_cartera[col_fecha_pago], dayfirst=True, errors="coerce"
            )
            fechas_pago = fechas_convertidas.dt.date

            # 3. Filtrar fechas menores o iguales a hoy
            mask_hasta_hoy = (fechas_pago <= hoy) & (fechas_pago.notna())
            df_hasta_hoy = df_cartera[mask_hasta_hoy]

            # 4. Sumar la columna correcta
            total_acumulado_hasta_hoy = df_hasta_hoy[pago_kamina_col].sum()

        col2.metric(
            label="Cartera de Clientes",
            value=f"${total_cartera:,.2f}",
            delta=f"Vencido hoy: ${total_acumulado_hasta_hoy:,.2f}",
        )
    else:
        col2.metric(label="Cartera Activa", value="Columnas no encontradas")
    col2.button(
        "Ver más", key="btn_cart", on_click=cambiar_vista, args=("cartera",)
    )

    # --- TARJETA 3: Revenue / Rebate ---
    if "Descuento" in df.columns:
        df_ytd["Descuento_Num"] = df_ytd["Descuento"].apply(_limpiar_a_float)
        df_mes_actual["Descuento_Num"] = df_mes_actual["Descuento"].apply(_limpiar_a_float)

        rev_ytd = df_ytd["Descuento_Num"].sum() * 0.80
        reb_mes = df_mes_actual["Descuento_Num"].sum() * 0.80

        col3.metric(
            label=f"Gross Profit ({anio_kpi})",
            value=f"${rev_ytd:,.2f}",
            delta=f"{nombre_mes_sel}: ${reb_mes:,.2f}",
            delta_color="off",
        )
    else:
        col3.metric(label="Revenue / Rebate", value="Columna no encontrada")

    col3.button(
        "Ver más", key="btn_desc", on_click=cambiar_vista, args=("descuentos",)
    )

    # --- TARJETA 4: Clientes Totales que han dispersado ---
    columna_cliente = "RFC Proveedor"
    if columna_cliente in df.columns:
        total_clientes_historico = df[columna_cliente].nunique()
        clientes_mes = (
            df_mes_actual[columna_cliente].nunique()
            if not df_mes_actual.empty
            else 0
        )

        col4.metric(
            label="Clientes Históricos",
            value=f"{total_clientes_historico:,}",
            delta=f"Activos {nombre_mes_sel}: {clientes_mes:,}",
            delta_color="off",
        )
    else:
        col4.metric(label="Total Clientes", value="Columna no encontrada")

    col4.button(
        "Ver más",
        key="btn_clientes",
        on_click=cambiar_vista,
        args=("clientes",),
    )