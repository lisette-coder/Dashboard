import streamlit as st
import pandas as pd
from datetime import datetime

from .constantes import NOMBRES_MESES
from .callbacks import cambiar_vista


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
    df_ytd = df_copia[df_copia["_Anio"] == anio_kpi]
    df_mes_actual = df_copia[
        (df_copia["_Anio"] == anio_kpi) & (df_copia["_Mes"] == mes_kpi)
    ]
    nombre_mes_sel = NOMBRES_MESES.get(mes_kpi, "Mes sel.")

    # KPIS PRINCIPALES
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)

    # --- TARJETA 1: Monto Total de Dispersiones ---
    monto_mes_actual = 0.0
    monto_dia_anterior = 0.0

    if "Monto Dispersado" in df_copia.columns and "_Fecha_Temp" in df_copia.columns:
        hoy = datetime.now().date()

        # 1. Si el año y mes seleccionados coinciden con el año y mes actual en curso
        if anio_kpi == hoy.year and mes_kpi == hoy.month:
            # Sumamos lo acumulado del mes hasta el día de hoy
            df_hasta_hoy = df_mes_actual[
                df_mes_actual["_Fecha_Temp"].dt.date <= hoy
            ]
            monto_mes_actual = df_hasta_hoy["Monto Dispersado"].sum()

            # Buscamos únicamente lo dispersado el día de ayer
            fecha_ayer = hoy - pd.Timedelta(days=1)
            monto_dia_anterior = df_mes_actual[
                df_mes_actual["_Fecha_Temp"].dt.date == fecha_ayer
            ]["Monto Dispersado"].sum()
        else:
            # Si se selecciona un mes/año pasado, muestra el total del mes y el último día con registros de ese mes
            monto_mes_actual = df_mes_actual["Monto Dispersado"].sum()
            if not df_mes_actual.empty:
                ultima_fecha_mes = df_mes_actual["_Fecha_Temp"].dt.date.max()
                monto_dia_anterior = df_mes_actual[
                    df_mes_actual["_Fecha_Temp"].dt.date == ultima_fecha_mes
                ]["Monto Dispersado"].sum()

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

    if pago_kamina_col in df.columns and estatus_pago_col in df.columns:
        df_copia_cartera = df.copy()
        df_copia_cartera[estatus_pago_col] = (
            df_copia_cartera[estatus_pago_col].astype(str).str.strip()
        )
        df_cartera = df_copia_cartera[
            df_copia_cartera[estatus_pago_col] == "To be paid"
        ]
        total_cartera = df_cartera[pago_kamina_col].sum()

        total_acumulado_hasta_hoy = 0.0
        if col_fecha_pago and not df_cartera.empty:
            hoy = datetime.now().date()
            fechas_convertidas = pd.to_datetime(
                df_cartera[col_fecha_pago], errors="coerce"
            )
            fechas_pago = fechas_convertidas.dt.date

            mask_hasta_hoy = (fechas_pago <= hoy) & (fechas_pago.notna())
            df_hasta_hoy = df_cartera[mask_hasta_hoy]
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
        rev_ytd = df_ytd["Descuento"].sum() * 0.80
        reb_mes = df_mes_actual["Descuento"].sum() * 0.80

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

    # --- TARJETA 5: Costo de Intereses ---
    col_mes_deuda = "Mes"
    col_interes_deuda = "IM"

    if (
        df_deuda is not None
        and not df_deuda.empty
        and col_interes_deuda in df_deuda.columns
        and col_mes_deuda in df_deuda.columns
    ):
        df_deuda_temp = df_deuda.copy()
        df_deuda_temp["_Fecha_Temp"] = pd.to_datetime(
            df_deuda_temp[col_mes_deuda], errors="coerce"
        )

        # 1. Obtener la fila única del mes seleccionado
        df_deuda_mes = df_deuda_temp[
            (df_deuda_temp["_Fecha_Temp"].dt.year == anio_kpi)
            & (df_deuda_temp["_Fecha_Temp"].dt.month == mes_kpi)
        ]

        # Extraemos directamente el valor de la fila si existe
        if not df_deuda_mes.empty:
            total_interes_mes = df_deuda_mes[col_interes_deuda].iloc[0]

            # 2. Cálculo de días totales y transcurridos
            dias_en_mes = pd.Period(f"{anio_kpi}-{mes_kpi:02d}").days_in_month
            hoy = datetime.now()

            if anio_kpi == hoy.year and mes_kpi == hoy.month:
                dias_transcurridos = hoy.day
            elif datetime(anio_kpi, mes_kpi, 1) < datetime(hoy.year, hoy.month, 1):
                dias_transcurridos = dias_en_mes  # Mes pasado completado
            else:
                dias_transcurridos = 0  # Mes futuro

            # 3. Prorrateo proporcional a hoy
            interes_acumulado_hoy = (
                (total_interes_mes / dias_en_mes) * dias_transcurridos
                if dias_en_mes > 0
                else 0.0
            )
        else:
            interes_acumulado_hoy = 0.0

        # 4. Cálculo del mes anterior para el Delta
        if mes_kpi == 1:
            mes_ant = 12
            anio_ant = anio_kpi - 1
        else:
            mes_ant = mes_kpi - 1
            anio_ant = anio_kpi

        df_deuda_mes_ant = df_deuda_temp[
            (df_deuda_temp["_Fecha_Temp"].dt.year == anio_ant)
            & (df_deuda_temp["_Fecha_Temp"].dt.month == mes_ant)
        ]
        total_interes_mes_ant = df_deuda_mes_ant[col_interes_deuda].sum()
        nombre_mes_ant = NOMBRES_MESES.get(mes_ant, f"Mes {mes_ant}")

        # Renderizado de la tarjeta
        col5.metric(
            label=f"Linea de deuda ({nombre_mes_sel})",
            value=f"${interes_acumulado_hoy:,.2f}",
            delta=f"Mes ant. ({nombre_mes_ant}): ${total_interes_mes_ant:,.2f}",
            delta_color="off",
        )
    else:
        col5.metric(label="Intereses Cobrados", value="Datos no encontrados")

    col5.button(
        "Ver más",
        key="btn_intereses",
        on_click=cambiar_vista,
        args=("intereses",),
    )