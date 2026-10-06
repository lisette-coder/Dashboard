from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
import plotly.graph_objects as go

from .constantes import NOMBRES_MESES
from .filtros import render_filtros_tiempo


def _limpiar_a_float(val):
    """Limpia cadenas con formato de moneda o porcentaje a float numérico."""
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = (
        str(val).replace("$", "").replace("%", "").replace(",", "").strip()
    )
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def render_barras_acumuladas(
    df_consolidado,
    df_deuda=None,
    date_column="Fecha de Dispersión",
    date_column_vencimiento="Fecha Vencimiento",
    date_column_deuda="Mes",
):

    st.markdown("---")
    st.subheader(
        "📊 Desglose Mensual: Gross Profit, Rebate Broker e Intereses por Mora"
    )

    # ============================================================
    # 1. VALIDACIONES
    # ============================================================
    if "Descuento" not in df_consolidado.columns:
        st.warning("No se encontró la columna 'Descuento' en los datos.")
        return

    # ============================================================
    # 2. FILTROS DE TIEMPO
    # ============================================================
    df_filtrado, tipo_filtro = render_filtros_tiempo(
        df_consolidado,
        sufijo_key="revenue_rebate_dual",
        date_column=date_column,
    )

    if df_filtrado.empty:
        st.warning("No hay datos disponibles para el filtro seleccionado.")
        return

    df_filtrado = df_filtrado.copy()

    # ============================================================
    # 3. LIMPIEZA DE DATOS NUMÉRICOS
    # ============================================================
    df_filtrado["Descuento_Num"] = df_filtrado["Descuento"].apply(_limpiar_a_float)

    col_interes = (
        "Interes acumulado"
        if "Interes acumulado" in df_filtrado.columns
        else "IP"
    )

    if col_interes in df_filtrado.columns:
        df_filtrado["Intereses_Num"] = df_filtrado[col_interes].apply(_limpiar_a_float)
    else:
        df_filtrado["Intereses_Num"] = 0.0

    # ============================================================
    # 4. FECHA DE DISPERSIÓN
    # ============================================================
    df_filtrado["Fecha_Disp_Clean"] = df_filtrado[date_column].apply(_parsear_fecha_flexible)
    df_filtrado["Mes_Dispersion"] = df_filtrado["Fecha_Disp_Clean"].dt.to_period("M")

    # ============================================================
    # 5. REVENUE
    # ============================================================
    rev_grouped = (
        df_filtrado.groupby("Mes_Dispersion", as_index=False)["Descuento_Num"]
        .sum()
        .rename(
            columns={
                "Mes_Dispersion": "Mes_Periodo",
                "Descuento_Num": "Total_Descuento",
            }
        )
    )

    rev_grouped["Gross Profit (80%)"] = rev_grouped["Total_Descuento"] * 0.80
    rev_grouped["Rebate (20%)"] = rev_grouped["Total_Descuento"] * 0.20

    # ============================================================
    # 6. INTERESES POR MORA
    # ============================================================
    col_venc = date_column_vencimiento

    if col_venc not in df_filtrado.columns:
        for c in df_filtrado.columns:
            if "vencimiento" in c.lower():
                col_venc = c
                break

    if col_venc in df_filtrado.columns:
        df_filtrado["Fecha_Venc_Clean"] = df_filtrado[col_venc].apply(_parsear_fecha_flexible)
        df_filtrado["Mes_Vencimiento"] = df_filtrado["Fecha_Venc_Clean"].dt.to_period("M")
        df_filtrado["Mes_Vencimiento"] = df_filtrado["Mes_Vencimiento"].fillna(
            df_filtrado["Mes_Dispersion"]
        )

        int_grouped = (
            df_filtrado.groupby("Mes_Vencimiento", as_index=False)["Intereses_Num"]
            .sum()
            .rename(
                columns={
                    "Mes_Vencimiento": "Mes_Periodo",
                    "Intereses_Num": "Intereses por Mora",
                }
            )
        )
    else:
        int_grouped = (
            df_filtrado.groupby("Mes_Dispersion", as_index=False)["Intereses_Num"]
            .sum()
            .rename(
                columns={
                    "Mes_Dispersion": "Mes_Periodo",
                    "Intereses_Num": "Intereses por Mora",
                }
            )
        )

    # ============================================================
    # 7. CONSOLIDAR REVENUE + INTERESES
    # ============================================================
    df_mes = pd.merge(rev_grouped, int_grouped, on="Mes_Periodo", how="outer").fillna(0.0)
    df_mes = df_mes.dropna(subset=["Mes_Periodo"])

    # ============================================================
    # 8. FILTRAR MESES (Mayo - Diciembre con datos)
    # ============================================================
    if not df_mes.empty:
        df_mes = df_mes[
            (df_mes["Mes_Periodo"].dt.month >= 5)
            & (df_mes["Mes_Periodo"].dt.month <= 12)
            & ((df_mes["Total_Descuento"] + df_mes["Intereses por Mora"]) > 0)
        ]

    if df_mes.empty:
        st.warning("No hay datos disponibles para el rango seleccionado.")
        return

    # ============================================================
    # 9 y 10. ORDENAR Y FORMATEAR MESES
    # ============================================================
    df_mes = df_mes.sort_values(by="Mes_Periodo")
    df_mes["Mes_Str"] = df_mes["Mes_Periodo"].apply(
        lambda p: f"{NOMBRES_MESES.get(p.month, str(p.month))} {p.year}"
        if pd.notna(p)
        else ""
    )

    # ============================================================
    # 11. MÉTRICAS FINANCIERAS
    # ============================================================
    df_mes["Revenue"] = df_mes["Gross Profit (80%)"] + df_mes["Rebate (20%)"]
    df_mes["Rebate Neto"] = df_mes["Rebate (20%)"] - df_mes["Intereses por Mora"]

    # ============================================================
    # 12. DATAFRAME PARA BARRAS
    # ============================================================
    df_plot = df_mes.melt(
        id_vars=["Mes_Str", "Revenue", "Rebate Neto", "Intereses por Mora"],
        value_vars=["Gross Profit (80%)", "Rebate (20%)"],
        var_name="Concepto",
        value_name="Monto",
    )

    # ============================================================
    # 13. CREAR GRÁFICA
    # ============================================================
   # ============================================================
    # 13. CREAR GRÁFICA CON PALETA DE VERDES (DEGRADADO A LA DERECHA)
    # ============================================================
    fig = px.bar(
        df_plot,
        x="Monto",
        y="Mes_Str",
        color="Concepto",
        orientation="h",
        title=f"Desglose Mensual Acumulado - ({tipo_filtro})",
        labels={
            "Mes_Str": "Mes",
            "Monto": "Monto ($)",
            "Concepto": "Concepto",
        },
        color_discrete_map={
            "Gross Profit (80%)": "#00875A",  # Verde profundo (Base izquierda)
            "Rebate (20%)": "#00E6A1",        # Verde menta/claro (Aclara hacia la derecha)
        },
    )

    # Desactivar hover en las barras apiladas individuales para no saturar
    fig.update_traces(hoverinfo="skip", hovertemplate=None, selector=dict(type="bar"))

    # ============================================================
    # 14. MARCADOR DE REVENUE NETO (Sin hover redundante)
    # ============================================================
    fig.add_trace(
        go.Scatter(
            x=df_mes["Revenue"],
            y=df_mes["Mes_Str"],
            mode="markers",
            marker=dict(
                symbol="diamond",
                size=12,
                color="#00C896",
                line=dict(color="white", width=1.5),
            ),
            name="Rebate Neto",
            showlegend=True,
            hoverinfo="skip",  # Evita duplicar el tooltip al pasar el cursor sobre el diamante
        )
    )

    # ============================================================
    # 15. HOVER ÚNICO Y CENTRALIZADO POR MES
    # ============================================================
    fig.add_trace(
        go.Scatter(
            x=df_mes["Revenue"],
            y=df_mes["Mes_Str"],
            mode="markers",
            marker=dict(
                size=30,
                color="rgba(0,0,0,0)",
            ),
            customdata=df_mes[
                [
                    "Revenue",
                    "Gross Profit (80%)",
                    "Rebate (20%)",
                    "Intereses por Mora",
                    "Rebate Neto",
                ]
            ].values,
            name="Resumen mensual",
            showlegend=False,
            hovertemplate=(
                "<b>Mes: %{y}</b>"
                "<br><br>"
                "Revenue: <b>$%{customdata[0]:,.2f}</b><br>"
                "Gross Profit (80%): <b>$%{customdata[1]:,.2f}</b><br>"
                "Rebate (20%): <b>$%{customdata[2]:,.2f}</b><br>"
                "Intereses por Mora: <b>$%{customdata[3]:,.2f}</b><br><br>"
                "<b>Rebate Neto: $%{customdata[4]:,.2f}</b>"
                "<extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor="#111827",
                bordercolor="#4B5563",
                font=dict(color="white", size=13),
            ),
        )
    )

    # ============================================================
    # 16. CONFIGURACIÓN VISUAL
    # ============================================================
    max_valor = df_mes["Revenue"].max() if not df_mes.empty else 1.0

    fig.update_layout(
        barmode="stack",
        xaxis_title="Monto ($)",
        yaxis_title="Mes",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend_title="Concepto",
        yaxis=dict(autorange="reversed"),
        xaxis=dict(range=[0, max_valor * 1.15]),
        margin=dict(l=0, r=40, t=40, b=0),
        hovermode="closest",  # Un solo tooltip activo a la vez
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
    )

    # ============================================================
    # 17. MOSTRAR GRÁFICA Y RESUMEN
    # ============================================================
    col_grafica, col_metricas = st.columns([3, 1])

    with col_grafica:
        st.plotly_chart(
            fig,
            use_container_width=True,
            key="bar_chart_revenue_stack_horizontal",
        )

    with col_metricas:
        st.markdown("### 📌 Resumen")

        total_revenue = df_mes["Revenue"].sum()
        total_gross_profit = df_mes["Gross Profit (80%)"].sum()
        total_rebate = df_mes["Rebate (20%)"].sum()
        total_intereses = df_mes["Intereses por Mora"].sum()
        total_rebate_neto = df_mes["Rebate (20%)"].sum() - df_mes["Intereses por Mora"].sum()

        st.metric(label="Revenue (100%)", value=f"${total_revenue:,.2f}")
        st.divider()
        st.metric(label="Gross Profit (80%)", value=f"${total_gross_profit:,.2f}")
        st.divider()
        st.metric(label="Rebate (20%)", value=f"${total_rebate:,.2f}")
        st.divider()
        st.metric(label="Intereses por Mora", value=f"${total_intereses:,.2f}")
        st.divider()
        st.metric(label="Rebate Neto", value=f"${total_rebate_neto:,.2f}")





def _parsear_fecha_flexible(val):
    """Convierte fechas desde Excel/Google Sheets considerando formatos M/D/YYYY y D/M/YYYY."""
    if pd.isna(val) or val is None or str(val).strip() == "":
        return pd.NaT
    if isinstance(val, (datetime, pd.Timestamp)):
        return val

    val_str = str(val).strip()

    # 1. Intentar parsear considerando formato Mes/Día/Año (M/D/YYYY) como en Google Sheets
    parsed = pd.to_datetime(val_str, errors="coerce", dayfirst=False)
    if pd.notna(parsed):
        return parsed

    # 2. Intentar parsear considerando formato Día/Mes/Año (D/M/YYYY)
    parsed = pd.to_datetime(val_str, errors="coerce", dayfirst=True)
    if pd.notna(parsed):
        return parsed

    # 3. Fallback para nombres de mes en español (ej: ago-2026)
    meses_map = {
        "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
        "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12
    }
    val_lower = val_str.lower()
    for m_nombre, m_num in meses_map.items():
        if m_nombre in val_lower:
            numeros = "".join([c for c in val_str if c.isdigit()])
            anio = int(numeros) if len(numeros) == 4 else (2000 + int(numeros) if len(numeros) == 2 else 2026)
            return pd.Timestamp(year=anio, month=m_num, day=1)

    return pd.NaT

def render_curva_revenue_vs_intereses(
    df_consolidado,
    df_deuda,
    date_column_conv="Fecha de Dispersión",
    date_column_deuda="Mes",
):
    """Renderiza la comparativa mensual entre Gross Profit (80%) e Intereses Pagados (IP de df_deuda)."""
    st.markdown("---")
    st.subheader("📈 Comparativa Mensual: Utilidad Bruta vs Intereses Pagados")

    # ============================================================
    # 1. APLICAR FILTRO DE TIEMPO IGUAL AL DEL GRÁFICO DE BARRAS
    # ============================================================
    df_filtrado, tipo_filtro = render_filtros_tiempo(
        df_consolidado,
        sufijo_key="revenue_vs_intereses_filter",
        date_column=date_column_conv,
    )

    if df_filtrado.empty:
        st.warning("No hay datos disponibles para el filtro seleccionado.")
        return

    df_filtrado = df_filtrado.copy()

    # ============================================================
    # 2. GROSS PROFIT (80% DEL REVENUE) POR MES
    # ============================================================
    df_c_grouped = pd.DataFrame(columns=["Mes_Periodo", "Gross_Profit"])

    if "Descuento" in df_filtrado.columns and date_column_conv in df_filtrado.columns:
        rev_temp = df_filtrado[[date_column_conv, "Descuento"]].copy()
        rev_temp["Descuento_Num"] = rev_temp["Descuento"].apply(_limpiar_a_float)
        rev_temp["Gross_Profit"] = rev_temp["Descuento_Num"] * 0.80

        rev_temp["Fecha_Clean"] = rev_temp[date_column_conv].apply(_parsear_fecha_flexible)
        rev_temp["Mes_Periodo"] = rev_temp["Fecha_Clean"].dt.to_period("M")

        df_c_grouped = (
            rev_temp.groupby("Mes_Periodo", as_index=False)["Gross_Profit"]
            .sum()
        )

    # ============================================================
    # 3. INTERESES PAGADOS (COLUMNA 'IP' DE df_deuda)
    # ============================================================
    df_d_grouped = pd.DataFrame(columns=["Mes_Periodo", "Intereses_Pagados"])

    if df_deuda is not None and not df_deuda.empty:
        df_deuda_copy = df_deuda.copy()

        col_interes = None
        for col in ["IP", "Intereses del periodo", "Intereses del mes"]:
            if col in df_deuda_copy.columns:
                col_interes = col
                break

        if col_interes and date_column_deuda in df_deuda_copy.columns:
            df_deuda_copy["Intereses_Pagados"] = df_deuda_copy[col_interes].apply(_limpiar_a_float)

            if "Intereses del mes" in df_deuda_copy.columns:
                val_mes = df_deuda_copy["Intereses del mes"].apply(_limpiar_a_float)
                df_deuda_copy["Intereses_Pagados"] = np.where(
                    df_deuda_copy["Intereses_Pagados"] > 0,
                    df_deuda_copy["Intereses_Pagados"],
                    val_mes,
                )

            df_deuda_copy["Fecha_Clean"] = df_deuda_copy[date_column_deuda].apply(_parsear_fecha_flexible)
            df_deuda_copy["Mes_Periodo"] = df_deuda_copy["Fecha_Clean"].dt.to_period("M")

            df_d_grouped = (
                df_deuda_copy.groupby("Mes_Periodo", as_index=False)["Intereses_Pagados"]
                .sum()
            )

    # ============================================================
    # 4. CONSOLIDAR AMBAS FUENTES
    # ============================================================
    if not df_c_grouped.empty or not df_d_grouped.empty:
        df_final = pd.merge(
            df_c_grouped, df_d_grouped, on="Mes_Periodo", how="outer"
        ).fillna(0.0)

        df_final = df_final.dropna(subset=["Mes_Periodo"])

        # Filtrar mismo rango de meses
        df_final = df_final[
            (df_final["Mes_Periodo"].dt.month >= 5)
            & (df_final["Mes_Periodo"].dt.month <= 12)
            & ((df_final["Gross_Profit"] + df_final["Intereses_Pagados"]) > 0)
        ].sort_values(by="Mes_Periodo")

        if df_final.empty:
            st.warning("No hay datos disponibles para el rango seleccionado.")
            return

        df_final["Mes_Str"] = df_final["Mes_Periodo"].apply(
            lambda p: f"{NOMBRES_MESES.get(p.month, str(p.month))} {p.year}"
            if pd.notna(p)
            else ""
        )

        df_plot = df_final.melt(
            id_vars=["Mes_Str"],
            value_vars=["Gross_Profit", "Intereses_Pagados"],
            var_name="Concepto",
            value_name="Monto",
        )

        nombres_leyenda = {
            "Gross_Profit": "Utilidad Bruta (Gross Profit 80%)",
            "Intereses_Pagados": "Intereses Pagados (IP)",
        }
        df_plot["Concepto_Label"] = df_plot["Concepto"].map(nombres_leyenda)

        # ============================================================
        # 5. RENDERIZAR GRÁFICA DE LÍNEAS
        # ============================================================
        fig = px.line(
            df_plot,
            x="Mes_Str",
            y="Monto",
            color="Concepto_Label",
            markers=True,
            title=f"Comparativa Mensual: Utilidad Bruta vs Intereses Pagados - ({tipo_filtro})",
            labels={
                "Mes_Str": "Mes",
                "Monto": "Monto ($)",
                "Concepto_Label": "Métrica",
            },
            color_discrete_map={
                "Utilidad Bruta (Gross Profit 80%)": "#0047AB",
                "Intereses Pagados (IP)": "#006847",
            },
        )

        fig.update_traces(
            line=dict(width=3),
            marker=dict(size=8),
            hovertemplate="Mes: %{x}<br>%{fullData.name}: <b>$%{y:,.2f}</b><extra></extra>",
        )

        fig.update_layout(
            xaxis_title="Mes",
            yaxis_title="Monto ($)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-45,
            legend_title="Métrica",
        )

        st.plotly_chart(
            fig, use_container_width=True, key="chart_revenue_vs_intereses"
        )
    else:
        st.warning(
            "No hay suficientes datos mensuales para graficar la comparativa."
        )


from datetime import datetime
import pandas as pd
import streamlit as st

def render_tabla_detalle_deuda(df_deuda):
    """Renderiza la tabla formateada del detalle de línea de deuda mostrando filas hasta el mes actual."""
    st.markdown("### 📋 Detalle de Línea de Deuda")

    if df_deuda is not None and not df_deuda.empty:
        df_tabla_deuda = df_deuda.copy()

        # Parsear fecha de la columna 'Mes' para orden y filtrado
        if "Mes" in df_tabla_deuda.columns:
            df_tabla_deuda["_Fecha_Temp"] = df_tabla_deuda["Mes"].apply(_parsear_fecha_flexible)

            # ------------------------------------------------------------
            # 1. FILTRAR FILAS HASTA EL MES ACTUAL (AÑO Y MES VIGENTE)
            # ------------------------------------------------------------
            hoy = datetime.now()
            # Primer día del mes actual para comparar períodos completos
            inicio_mes_actual = pd.Timestamp(year=hoy.year, month=hoy.month, day=1)

            mask_hasta_hoy = df_tabla_deuda["_Fecha_Temp"].apply(
                lambda dt: dt.to_period("M") <= inicio_mes_actual.to_period("M") if pd.notna(dt) else False
            )
            df_tabla_deuda = df_tabla_deuda[mask_hasta_hoy].copy()

        if df_tabla_deuda.empty:
            st.warning("No hay registros de deuda para mostrar hasta el mes actual.")
            return

        # ------------------------------------------------------------
        # 2. RENOMBRAR COLUMNAS
        # ------------------------------------------------------------
        renombres = {
            "SC": "Solicitudes de Capital",
            "Solicitudes Capital": "Solicitudes de Capital",
            "SC (acum)": "Saldo de Capital (acumulado)",
            "Saldo de Capital (acum)": "Saldo de Capital (acumulado)",
            "TM": "Tasa Mensual",
            "IP": "Intereses del periodo",
            "AI": "Acumulado Intereses",
        }
        df_tabla_deuda = df_tabla_deuda.rename(columns=renombres)

        # ------------------------------------------------------------
        # 3. DEFINIR ORDEN DESEADO DE COLUMNAS
        # ------------------------------------------------------------
        columnas_ordenadas = [
            "Mes",
            "Solicitudes de Capital",
            "Saldo de Capital (acumulado)",
            "Tasa Mensual",
            "Intereses del periodo",
            "Acumulado Intereses",
        ]

        # Conservar solo las columnas que existan en el DataFrame
        cols_existentes = [col for col in columnas_ordenadas if col in df_tabla_deuda.columns]

        if cols_existentes:
            # Formatear la columna 'Mes' a NombreMes-Año
            if "Mes" in cols_existentes and "_Fecha_Temp" in df_tabla_deuda.columns:
                df_tabla_deuda["Mes"] = df_tabla_deuda["_Fecha_Temp"].apply(
                    lambda dt: f"{NOMBRES_MESES.get(dt.month, '')}-{dt.year}" if pd.notna(dt) else ""
                )

            # Formatear columnas numéricas de Moneda ($)
            cols_moneda = [
                col for col in cols_existentes if col not in ["Mes", "Tasa Mensual"]
            ]

            for col in cols_moneda:
                df_tabla_deuda[col] = df_tabla_deuda[col].apply(_limpiar_a_float)
                df_tabla_deuda[col] = df_tabla_deuda[col].apply(lambda x: f"${x:,.2f}")

            # Formatear columna de Porcentaje (%)
            if "Tasa Mensual" in cols_existentes:
                df_tabla_deuda["Tasa Mensual"] = df_tabla_deuda["Tasa Mensual"].apply(_limpiar_a_float)
                df_tabla_deuda["Tasa Mensual"] = df_tabla_deuda["Tasa Mensual"].apply(
                    lambda x: f"{x * 100:,.2f}%" if 0 < x <= 1 else f"{x:,.2f}%"
                )

            # Renderizar la tabla con las columnas ordenadas
            st.dataframe(
                df_tabla_deuda[cols_existentes].dropna(how="all"),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("No se encontraron las columnas especificadas en los datos de deuda.")
    else:
        st.warning("No hay datos disponibles para la línea de deuda.")