import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar
from utils import obtener_mora_congelada_consolidada

# Asegúrate de tener importado NOMBRES_MESES desde tu módulo de constantes
from .constantes import NOMBRES_MESES


def render_tarjetas_kpi(
    df,
    df_deuda=None,
    columna_metrica="Monto Liquidado",
    columna_por_cobrar="Monto a Pagar a Kamina",
    tipo_filtro="Período Seleccionado",
    anio_kpi=None,
    mes_kpi=None,
):
    """Calcula y muestra el bloque de 5 tarjetas KPI principales en formato vertical."""
    if df is None or df.empty:
        st.warning("No hay datos disponibles para mostrar las tarjetas.")
        return

    # Determinar año y mes por defecto
    hoy = datetime.now()
    anio_kpi = anio_kpi if anio_kpi is not None else hoy.year
    mes_kpi = mes_kpi if mes_kpi is not None else hoy.month

    df_copy = df.copy()
    df_copy.columns = df_copy.columns.str.strip()

    # ---------------------------------------------------------
    # 1. Adelantos Liquidados (PAID)
    # ---------------------------------------------------------
    col_estatus = "Estatus Pago a Kamina"
    col_liquidado = (
        columna_metrica if columna_metrica in df_copy.columns else "Monto Liquidado"
    )

    monto_liquidados = 0.0
    if col_estatus in df_copy.columns and col_liquidado in df_copy.columns:
        mask_paid = df_copy[col_estatus].astype(str).str.strip().str.upper() == "PAID"
        monto_liquidados = (
            pd.to_numeric(df_copy.loc[mask_paid, col_liquidado], errors="coerce")
            .fillna(0)
            .sum()
        )

    # ---------------------------------------------------------
    # 2. Capital en uso (To be paid)
    # ---------------------------------------------------------
    col_cobrar = (
        columna_por_cobrar
        if columna_por_cobrar in df_copy.columns
        else "Monto a Pagar a Kamina"
    )

    capital_en_uso = 0.0
    if col_estatus in df_copy.columns and col_cobrar in df_copy.columns:
        mask_tobepaid = (
            df_copy[col_estatus].astype(str).str.strip().str.lower() == "to be paid"
        )
        capital_en_uso = (
            pd.to_numeric(df_copy.loc[mask_tobepaid, col_cobrar], errors="coerce")
            .fillna(0)
            .sum()
        )

    # ---------------------------------------------------------
    # 3. Capital / Fondeo Total: Exclusivamente SC (acum)
    # 5. Línea de deuda: Exclusivamente IP
    # ---------------------------------------------------------
    total_capital_fondeo = 0.0
    ip_mes_actual = 0.0
    ip_mes_ant = 0.0

    if df_deuda is not None and not df_deuda.empty:
        df_d = df_deuda.copy()
        df_d.columns = df_d.columns.str.strip()

        if "Mes" in df_d.columns:
            df_d["_Fecha"] = pd.to_datetime(df_d["Mes"], errors="coerce")

            # Filtro exacto por mes y año seleccionado
            mask_actual = (df_d["_Fecha"].dt.year == anio_kpi) & (
                df_d["_Fecha"].dt.month == mes_kpi
            )
            df_actual = df_d[mask_actual]

            if not df_actual.empty:
                # Se extrae estrictamente la columna SC (acum)
                if "SC (acum)" in df_actual.columns:
                    val_sc_acum = pd.to_numeric(
                        df_actual["SC (acum)"], errors="coerce"
                    ).iloc[0]
                    total_capital_fondeo = (
                        val_sc_acum if pd.notna(val_sc_acum) else 0.0
                    )

                # Valor IP del mes actual
                if "IP" in df_actual.columns:
                    val_ip = pd.to_numeric(df_actual["IP"], errors="coerce").iloc[0]
                    ip_mes_actual = val_ip if pd.notna(val_ip) else 0.0

            # Mes anterior para la delta de la Tarjeta 5
            mes_ant = 12 if mes_kpi == 1 else mes_kpi - 1
            anio_ant = anio_kpi - 1 if mes_kpi == 1 else anio_kpi

            mask_ant = (df_d["_Fecha"].dt.year == anio_ant) & (
                df_d["_Fecha"].dt.month == mes_ant
            )
            df_ant = df_d[mask_ant]

            if not df_ant.empty and "IP" in df_ant.columns:
                val_ip_ant = pd.to_numeric(df_ant["IP"], errors="coerce").iloc[0]
                ip_mes_ant = val_ip_ant if pd.notna(val_ip_ant) else 0.0

    # ---------------------------------------------------------
    # 4. Capital disponible
    # ---------------------------------------------------------
    capital_disponible = max(0.0, total_capital_fondeo - capital_en_uso)

    # ---------------------------------------------------------
    # RENDERIZADO VERTICAL (Insights Lateral)
    # ---------------------------------------------------------
    st.markdown("### ✨ Insights del periodo")

    # 1. Adelantos Liquidados
    with st.container(border=True):
        st.caption(f"💼 Adelantos Liquidados ({tipo_filtro})")
        st.subheader(f"${monto_liquidados:,.2f}")
        st.caption("Monto total liquidado en el período.")

    # 2. Capital en uso
    with st.container(border=True):
        st.caption("💳 Capital en uso")
        st.subheader(f"${capital_en_uso:,.2f}")
        st.caption("Monto asignado listo o pendiente de cobro.")

    # 3. Capital / Fondeo Total
    with st.container(border=True):
        st.caption("🏛️ Capital / Fondeo Total")
        st.subheader(f"${total_capital_fondeo:,.2f}")
        st.caption("Total de fondeo acumulado (SC).")

    # 4. Capital disponible
    with st.container(border=True):
        st.caption("🟢 Capital disponible")
        st.subheader(f"${capital_disponible:,.2f}")
        st.caption("Listo para nuevas operaciones.")


def render_curva_cartera_dual(
    df,
    columna_metrica="Monto Dispersado",
    titulo_base="Evolución de Cartera Dual",
    date_column="Fecha Vencimiento",
    tipo_filtro="Año Completo",
):
    """Renderiza únicamente el gráfico de líneas de comparación diaria."""
    st.markdown("---")
    st.subheader(f"📈 {titulo_base}")

    if (
        df is None
        or df.empty
        or date_column not in df.columns
        or "Estatus Pago a Kamina" not in df.columns
    ):
        st.warning(
            f"Faltan columnas necesarias ('{date_column}' o 'Estatus Pago a Kamina') en los datos."
        )
        return

    df_pendiente = df[df["Estatus Pago a Kamina"] == "To be paid"].copy()
    df_pagado = df[df["Estatus Pago a Kamina"] == "PAID"].copy()

    col_grafica = (
        columna_metrica if columna_metrica in df.columns else "Monto Dispersado"
    )

    df_pendiente["Fecha_Dia"] = pd.to_datetime(
        df_pendiente[date_column], errors="coerce"
    ).dt.date
    df_pagado["Fecha_Dia"] = pd.to_datetime(
        df_pagado[date_column], errors="coerce"
    ).dt.date

    df_pend_grouped = (
        df_pendiente.groupby("Fecha_Dia")[col_grafica].sum().reset_index()
    )
    df_pend_grouped["Tipo_Flujo"] = "Pendiente / Por Pagar"

    df_pag_grouped = (
        df_pagado.groupby("Fecha_Dia")[col_grafica].sum().reset_index()
    )
    df_pag_grouped["Tipo_Flujo"] = "Pagado / Liquidado"

    df_final = pd.concat([df_pend_grouped, df_pag_grouped]).dropna(
        subset=["Fecha_Dia"]
    )
    df_final = df_final.sort_values(by="Fecha_Dia")

    if not df_final.empty:
        df_final["Fecha_Str"] = pd.to_datetime(
            df_final["Fecha_Dia"]
        ).dt.strftime("%Y-%m-%d")

        fig = px.line(
            df_final,
            x="Fecha_Str",
            y=col_grafica,
            color="Tipo_Flujo",
            markers=True,
            title=f"{titulo_base} - Vista Diaria ({tipo_filtro})",
            labels={
                "Fecha_Str": "Día",
                col_grafica: f"{titulo_base} ($)",
                "Tipo_Flujo": "Estatus",
            },
            color_discrete_map={
                "Pendiente / Por Pagar": "darkorange",
                "Pagado / Liquidado": "forestgreen",
            },
        )
        fig.update_traces(
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate="Día: %{x}<br>Monto: $%{y:,.2f}<extra></extra>",
        )
        fig.update_layout(
            xaxis_title="Día",
            yaxis_title=f"{titulo_base} ($)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-45,
            legend_title="Flujo",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(
            "No hay datos diarios disponibles para graficar en este rango."
        )




def render_dona_composicion_capital(
    df,
    df_deuda,
    columna_metrica="Monto a Pagar a Kamina",
    columna_estatus="Estatus Pago a Kamina",
    columna_deuda_sc="SC (acum)",
):
    """Genera un gráfico de dona compuesto por Capital Colocado (To be paid) y Capital Disponible."""
    st.markdown("### 🍩 Composición del Capital")

    # 1. Validar existencia de datos
    if df is None or df.empty or df_deuda is None or df_deuda.empty:
        st.warning(
            "No se cuenta con información suficiente para calcular la composición del capital."
        )
        return

    # Crear copias para evitar alterar DataFrames fuera de la función
    df = df.copy()
    df_deuda = df_deuda.copy()

    # Normalizar encabezados (quitar espacios al inicio/final)
    df.columns = df.columns.str.strip()
    df_deuda.columns = df_deuda.columns.str.strip()

    # 2. AUTO-CORRECCIÓN: Intercambio si se pasaron al revés
    if (
        columna_deuda_sc in df.columns
        and columna_deuda_sc not in df_deuda.columns
    ):
        df, df_deuda = df_deuda, df

    # 3. Validación de columnas requeridas
    if columna_deuda_sc not in df_deuda.columns:
        st.warning(
            f"La columna '{columna_deuda_sc}' no se encontró en el DataFrame de Deuda.\n\n"
            f"**Columnas detectadas en Deuda:** `{list(df_deuda.columns)}`"
        )
        return

    if columna_metrica not in df.columns or columna_estatus not in df.columns:
        st.warning(
            f"Faltan columnas requeridas en el DataFrame de cartera ('{columna_metrica}' o '{columna_estatus}').\n\n"
            f"**Columnas detectadas:** `{list(df.columns)}`"
        )
        return

    # 4. Obtención del Capital Total
    serie_sc = pd.to_numeric(
        df_deuda[columna_deuda_sc], errors="coerce"
    ).dropna()
    if serie_sc.empty:
        st.warning(
            "La columna 'SC (acum)' no contiene datos numéricos válidos."
        )
        return

    capital_total = serie_sc.iloc[-1]

    # 5. Cálculos dinámicos
    por_pagar = pd.to_numeric(
        df[df[columna_estatus].astype(str).str.strip() == "To be paid"][
            'Monto a Pagar a Kamina'
        ],
        errors="coerce",
    ).sum()

    disponible = max(0, capital_total - por_pagar)

    # 6. Gráfico Plotly
    labels = ["Capital Disponible", "Por Pagar (Colocado)"]
    values = [disponible, por_pagar]
    colors = ["#2a9d8f", "#e9c46a"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.65,
                textinfo="percent",
                hoverinfo="label+value+percent",
                hovertemplate="<b>%{label}</b><br>Monto: $%{value:,.2f}<br>Porcentaje: %{percent}<extra></extra>",
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
            )
        ]
    )

    fig.update_layout(
        annotations=[
            dict(
                text=f"<b>Capital Total</b><br><span style='font-size:16px; color:#2a9d8f;'>${capital_total:,.2f}</span>",
                x=0.5,
                y=0.5,
                font=dict(size=14),
                showarrow=False,
            )
        ],
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
        ),
        height=380,
        margin=dict(l=20, r=20, t=30, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)

def render_barras_colocado_mensual(
    df, date_column="Fecha de Dispersión", monto_column="Monto Dispersado"
):
    """Genera un gráfico de barras horizontales mostrando el monto colocado por mes."""
    st.markdown("### 📊 Capital Colocado por Mes")

    if df is None or df.empty:
        st.warning("No hay datos suficientes para el gráfico de barras.")
        return

    # Limpiar espacios en nombres de columna del DataFrame
    col_monto = (
        monto_column if monto_column in df.columns else monto_column.strip()
    )

    if date_column not in df.columns or col_monto not in df.columns:
        st.warning("No hay datos suficientes para el gráfico de barras.")
        return

    df_temp = df[[date_column, col_monto]].copy()
    df_temp["Fecha"] = pd.to_datetime(df_temp[date_column], errors="coerce")
    df_temp["Monto"] = pd.to_numeric(
        df_temp[col_monto], errors="coerce"
    ).fillna(0)
    df_temp = df_temp.dropna(subset=["Fecha"])

    if df_temp.empty:
        st.warning("No hay registros válidos con fechas para graficar.")
        return

    # Usar resample de forma compatible con múltiples versiones de Pandas
    try:
        df_mensual = (
            df_temp.set_index("Fecha").resample("ME")["Monto"].sum().reset_index()
        )
    except ValueError:
        df_mensual = (
            df_temp.set_index("Fecha").resample("M")["Monto"].sum().reset_index()
        )

    df_mensual["Mes_Nombre"] = (
        df_mensual["Fecha"].dt.month.map(NOMBRES_MESES)
        + " "
        + df_mensual["Fecha"].dt.year.astype(str)
    )

    # Calcular el valor máximo para extender dinámicamente el eje X
    monto_max = df_mensual["Monto"].max() if not df_mensual.empty else 0

    fig = go.Figure(
        go.Bar(
            x=df_mensual["Monto"],
            y=df_mensual["Mes_Nombre"],
            orientation="h",
            marker=dict(
                color=df_mensual["Monto"],
                colorscale="Blues",
                showscale=False,
            ),
            text=[f"${m:,.0f}" for m in df_mensual["Monto"]],
            textposition="outside",
            cliponaxis=False,  # CRUCIAL: evita el recorte del texto en el borde del eje
            hovertemplate="<b>%{y}</b><br>Dispersado: $%{x:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            title="",
            range=[0, monto_max * 1.25],  # Otorga un 25% extra de espacio a la derecha
        ),
        yaxis=dict(showgrid=False, autorange="reversed"),
        height=380,
        margin=dict(l=10, r=80, t=30, b=20),  # Margen derecho ampliado de 40 a 80
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)


def calcular_deuda_diaria_vencida(
    df,
    tasa_mensual=0.035,
    col_fecha_venc="Fecha Vencimiento",
    col_monto="Monto a Pagar a Kamina",
    col_estatus="Estatus Pago a Kamina",
):
  """Agrupa las facturas por día de vencimiento, sumando el monto total por día

  y calculando los días de atraso e intereses moratorios diarios.
  """
  if df is None or df.empty:
    return pd.DataFrame(), 0, 0.0, 0.0, 0

  df_copy = df.copy()
  df_copy.columns = df_copy.columns.str.strip()

  if col_fecha_venc not in df_copy.columns or col_monto not in df_copy.columns:
    return pd.DataFrame(), 0, 0.0, 0.0, 0

  # Normalización de datos
  df_copy['_Fecha_Venc'] = pd.to_datetime(
      df_copy[col_fecha_venc], errors='coerce'
  )
  df_copy['_Monto'] = pd.to_numeric(df_copy[col_monto], errors='coerce').fillna(
      0
  )

  # Filtrar solo facturas vencidas
  hoy = datetime.now()
  dias_del_mes = calendar.monthrange(hoy.year, hoy.month)[1]
  tasa_diaria = tasa_mensual / dias_del_mes

  mask_vencidas = (df_copy['_Fecha_Venc'] < hoy) & (df_copy['_Monto'] > 0)

  if col_estatus in df_copy.columns:
    mask_vencidas &= (
        df_copy[col_estatus].astype(str).str.strip().str.lower() == 'to be paid'
    )

  df_vencidas = df_copy[mask_vencidas].copy()

  if df_vencidas.empty:
    return pd.DataFrame(), 0, 0.0, 0.0, 0

  # Extraer solo la fecha (sin horas) para agrupar por día
  df_vencidas['Fecha_Dia'] = df_vencidas['_Fecha_Venc'].dt.date

  # 📌 AGRUPACIÓN POR DÍA
  df_agrupado = (
      df_vencidas.groupby('Fecha_Dia')
      .agg(
          Monto_Total=('_Monto', 'sum'),
          Cantidad_Facturas=('_Monto', 'count'),
      )
      .reset_index()
  )

  # Cálculo de días de atraso e intereses por cada fecha acumulada
  df_agrupado['Dias_Atraso'] = df_agrupado['Fecha_Dia'].apply(
      lambda fecha: (hoy.date() - fecha).days
  )
  df_agrupado['Interes_Mora'] = (
      df_agrupado['Monto_Total'] * tasa_diaria * df_agrupado['Dias_Atraso']
  )

  # Ordenar por la fecha más antigua / mayor retraso primero
  df_agrupado = df_agrupado.sort_values(by='Dias_Atraso', ascending=False)

  # Totales globales
  total_facturas = df_vencidas.shape[0]
  monto_pendiente_total = df_agrupado['Monto_Total'].sum()
  interes_acumulado_total = df_agrupado['Interes_Mora'].sum()
  mayor_atraso = df_agrupado['Dias_Atraso'].max()

  return (
      df_agrupado,
      total_facturas,
      monto_pendiente_total,
      interes_acumulado_total,
      mayor_atraso,
  )


# ---------------------------------------------------------
# COMPONENTE UI: Tabla/Lista de Facturas Vencidas
# ---------------------------------------------------------
def render_seccion_facturas_vencidas(df, tasa_mensual=0.035):
  """Renderiza las facturas vencidas agrupadas exactamente por su fecha original de vencimiento."""
  df_historial = obtener_mora_congelada_consolidada()
  usando_congelados = False

  if not df_historial.empty:
    usando_congelados = True

    # 1. Asegurar formato de fecha sin horas
    df_historial["Fecha_Vencimiento"] = pd.to_datetime(
        df_historial["Fecha_Vencimiento"]
    ).dt.floor("D")

    # 2. Recalcular días de retraso de forma exacta a la fecha de hoy
    hoy = pd.to_datetime("today").floor("D")
    df_historial["Dias_Atraso_Real"] = (
        hoy - df_historial["Fecha_Vencimiento"]
    ).dt.days

    # KPIs Globales (Suma $18,831,734.82 exacta)
    total_facturas = len(df_historial)
    monto_pendiente = df_historial["Monto_Base"].sum()
    interes_acum = df_historial["Interes_Mora_Congelado"].sum()
    max_atraso = (
        int(df_historial["Dias_Atraso_Real"].max())
        if not df_historial.empty
        else 0
    )

    # 3. Agrupar ESTRICTAMENTE por Fecha_Vencimiento
    df_dias = (
        df_historial.groupby("Fecha_Vencimiento")
        .agg(
            Cantidad_Facturas=("Factura_ID", "count"),
            Monto_Total=("Monto_Base", "sum"),
            Interes_Mora=("Interes_Mora_Congelado", "sum"),
            Dias_Atraso=("Dias_Atraso_Real", "max"),
        )
        .reset_index()
    )

    df_dias.rename(columns={"Fecha_Vencimiento": "Fecha_Dia"}, inplace=True)
    df_dias.sort_values(by="Fecha_Dia", ascending=False, inplace=True)

  else:
    (
        df_dias,
        total_facturas,
        monto_pendiente,
        interes_acum,
        max_atraso,
    ) = calcular_deuda_diaria_vencida(df, tasa_mensual=tasa_mensual)

  # -------------------------------------------------------------
  # INTERFAZ GRÁFICA STREAMLIT
  # -------------------------------------------------------------
  with st.container(border=True):
    c_titulo, c_badge = st.columns([0.7, 0.3])
    with c_titulo:
      st.markdown("### ⚠️ Facturas Vencidas por Día")
    with c_badge:
      if usando_congelados:
        st.caption("🔒 **Cierre Congelado (JSON)**")
      else:
        st.caption("⚡ **Cálculo en Vivo**")

    # CSS Métricas
    st.markdown(
        """
            <style>
            [data-testid="stMetricValue"] {
                font-size: 1.15rem !important;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            [data-testid="stMetricLabel"] {
                font-size: 0.8rem !important;
            }
            </style>
            """,
        unsafe_allow_html=True,
    )

    # KPIs Superiores
    k1, k2 = st.columns(2)
    k1.metric("Facturas Vencidas", f"{total_facturas}")
    k2.metric("Monto Pendiente", f"${monto_pendiente:,.2f}")

    k3, k4 = st.columns(2)
    k3.metric("Interés Acumulado", f"${interes_acum:,.2f}")
    k4.metric("Mayor Atraso", f"{max_atraso}d")

    st.divider()

    if not df_dias.empty:
      st.caption(
          f"Tasa: **{tasa_mensual*100:.1f}% mens.** (calculado por días"
          " transcurridos)"
      )

      with st.container(height=240):
        for _, row in df_dias.iterrows():
          c_info, c_monto = st.columns([0.55, 0.45])
          fecha_fmt = row["Fecha_Dia"].strftime("%d de %b, %Y")

          with c_info:
            st.markdown(f"🗓️ **{fecha_fmt}**")
            st.caption(
                f"**{int(row['Dias_Atraso'])} días de retraso** •"
                f" ({row['Cantidad_Facturas']} fact.)"
            )

          with c_monto:
            st.markdown(f"**${row['Monto_Total']:,.2f}**")
            st.caption(f"Interés: **+${row['Interes_Mora']:,.2f}**")

          st.markdown(
              "<hr style='margin: 3px 0px; border-top: 1px dashed #444;'>",
              unsafe_allow_html=True,
          )
    else:
      st.info("🎉 No hay días con pagos pendientes.")