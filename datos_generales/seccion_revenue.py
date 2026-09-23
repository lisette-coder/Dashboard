import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from .constantes import NOMBRES_MESES

from .filtros import render_filtros_tiempo

def render_curva_revenue_rebate_dual(df, date_column="Fecha de Dispersión"):
    """Renderiza evolución y desglose diario de Revenue (80%) y Rebate (20%)."""
    st.markdown("---")
    st.subheader("📈 Evolución Diaria: Revenue Kamina vs. Rebate Broker")

    if "Descuento" not in df.columns:
        st.warning("No se encontró la columna 'Descuento' en los datos.")
        return

    df_filtrado, tipo_filtro = render_filtros_tiempo(
        df, sufijo_key="revenue_rebate_dual", date_column=date_column
    )

    if date_column not in df_filtrado.columns:
        st.warning(
            f"No se encontró la columna de fecha '{date_column}' en los datos."
        )
        return

    if not df_filtrado.empty:
        total_descuento = df_filtrado["Descuento"].sum()
        total_revenue = total_descuento * 0.80
        total_rebate = total_descuento * 0.20

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label=f"Ingresos Kamina ({tipo_filtro})",
                value=f"${total_descuento:,.2f}",
            )
        with col2:
            st.metric(
                label=f"Utilidad Bruta ({tipo_filtro})",
                value=f"${total_revenue:,.2f}",
            )
        with col3:
            st.metric(
                label=f"Rebate/Costo Broker ({tipo_filtro})",
                value=f"${total_rebate:,.2f}",
            )

    df_filtrado["Fecha_Dia"] = pd.to_datetime(
        df_filtrado[date_column], errors="coerce"
    ).dt.date
    df_filtrado["Revenue Kamina"] = df_filtrado["Descuento"] * 0.80
    df_filtrado["Rebate Broker"] = df_filtrado["Descuento"] * 0.20

    df_rev_grouped = (
        df_filtrado.groupby("Fecha_Dia")["Revenue Kamina"].sum().reset_index()
    )
    df_rev_grouped["Tipo_Flujo"] = "Revenue Kamina (80%)"
    df_rev_grouped["Monto"] = df_rev_grouped["Revenue Kamina"]

    df_reb_grouped = (
        df_filtrado.groupby("Fecha_Dia")["Rebate Broker"].sum().reset_index()
    )
    df_reb_grouped["Tipo_Flujo"] = "Rebate Broker (20%)"
    df_reb_grouped["Monto"] = df_reb_grouped["Rebate Broker"]

    df_final = pd.concat(
        [
            df_rev_grouped[["Fecha_Dia", "Tipo_Flujo", "Monto"]],
            df_reb_grouped[["Fecha_Dia", "Tipo_Flujo", "Monto"]],
        ]
    ).dropna(subset=["Fecha_Dia"])
    df_final = df_final.sort_values(by="Fecha_Dia")

    if not df_final.empty:
        df_final["Fecha_Str"] = pd.to_datetime(
            df_final["Fecha_Dia"]
        ).dt.strftime("%Y-%m-%d")

        fig = px.line(
            df_final,
            x="Fecha_Str",
            y="Monto",
            color="Tipo_Flujo",
            markers=True,
            title=f"Revenue vs Rebate - Vista Diaria ({tipo_filtro})",
            labels={
                "Fecha_Str": "Día",
                "Monto": "Monto ($)",
                "Tipo_Flujo": "Concepto",
            },
            color_discrete_map={
                "Revenue Kamina (80%)": "#0047AB",
                "Rebate Broker (20%)": "#8A2BE2",
            },
        )
        fig.update_traces(
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate="Día: %{x}<br>Monto: $%{y:,.2f}<extra></extra>",
        )
        fig.update_layout(
            xaxis_title="Día",
            yaxis_title="Monto ($)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-45,
            legend_title="Concepto",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos diarios disponibles para graficar en este rango.")



def render_curva_revenue_vs_intereses(
    df_consolidado,
    df_deuda,
    date_column_conv="Fecha de Dispersión",
    date_column_deuda="Mes",
):
    df_c_grouped = pd.DataFrame(columns=["Mes_Periodo", "Revenue_Kamina"])
    if (
        "Descuento" in df_consolidado.columns
        and date_column_conv in df_consolidado.columns
    ):
        rev_temp = df_consolidado[[date_column_conv, "Descuento"]].copy()
        rev_temp["Revenue_Kamina"] = (
            pd.to_numeric(rev_temp["Descuento"], errors="coerce").fillna(0)
            * 0.80
        )
        rev_temp["Mes_Periodo"] = pd.to_datetime(
            rev_temp[date_column_conv], errors="coerce"
        ).dt.to_period("M")

        df_c_grouped = rev_temp.groupby("Mes_Periodo", as_index=False)[
            "Revenue_Kamina"
        ].sum()

    df_d_grouped = pd.DataFrame(columns=["Mes_Periodo", "Intereses_Cobrados"])
    if df_deuda is not None and not df_deuda.empty:
        col_interes = "IP"
        if (
            col_interes in df_deuda.columns
            and date_column_deuda in df_deuda.columns
        ):
            int_temp = df_deuda[[date_column_deuda, col_interes]].copy()
            int_temp["Intereses_Cobrados"] = pd.to_numeric(
                int_temp[col_interes], errors="coerce"
            ).fillna(0)
            int_temp["Mes_Periodo"] = pd.to_datetime(
                int_temp[date_column_deuda], errors="coerce"
            ).dt.to_period("M")

            df_d_grouped = int_temp.groupby("Mes_Periodo", as_index=False)[
                "Intereses_Cobrados"
            ].sum()

    if not df_c_grouped.empty:
        if not df_d_grouped.empty:
            df_final = pd.merge(
                df_c_grouped, df_d_grouped, on="Mes_Periodo", how="outer"
            ).fillna(0)
        else:
            df_final = df_c_grouped
            df_final["Intereses_Cobrados"] = 0.0

        df_final = df_final.sort_values(by="Mes_Periodo")
        df_final["Mes_Str"] = df_final["Mes_Periodo"].astype(str)

        fig = px.line(
            df_final,
            x="Mes_Str",
            y=["Revenue_Kamina", "Intereses_Cobrados"],
            markers=True,
            title="Comparativa Mensual: Revenue Kamina vs Intereses Cobrados",
            labels={
                "Mes_Str": "Mes",
                "value": "Monto ($)",
                "variable": "Concepto",
            },
            color_discrete_map={
                "Revenue_Kamina": "#0047AB",
                "Intereses_Cobrados": "#8A2BE2",
            },
        )

        new_names = {
            "Revenue_Kamina": "Utilidad Bruta",
            "Intereses_Cobrados": "Intereses Cobrados",
        }
        fig.for_each_trace(
            lambda t: t.update(name=new_names.get(t.name, t.name))
        )

        fig.update_traces(
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate="Mes: %{x}<br>Monto: $%{y:,.2f}<extra></extra>",
        )

        fig.update_layout(
            xaxis_title="Mes",
            yaxis_title="Monto ($)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-45,
            legend_title="Métrica",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="chart_revenue_vs_intereses",  # Previene error de ID duplicado
        )
    else:
        st.warning("No hay suficientes datos mensuales para graficar.")



def render_tabla_detalle_deuda(df_deuda):
    """Renderiza la tabla formateada del detalle de línea de deuda con variables originales."""
    st.markdown("### 📋 Detalle de Línea de Deuda")

    if df_deuda is not None and not df_deuda.empty:
        df_tabla_deuda = df_deuda.copy()

        # 1. Asegurar formato datetime para filtrar y formatear
        if "Mes" in df_tabla_deuda.columns:
            df_tabla_deuda["_Fecha_Temp"] = pd.to_datetime(
                df_tabla_deuda["Mes"], errors="coerce"
            )

            # 2. Filtrar registros hasta el mes actual
            hoy = datetime.now()
            primer_dia_mes_siguiente = (
                datetime(hoy.year, hoy.month + 1, 1)
                if hoy.month < 12
                else datetime(hoy.year + 1, 1, 1)
            )

            df_tabla_deuda = df_tabla_deuda[
                df_tabla_deuda["_Fecha_Temp"] < primer_dia_mes_siguiente
            ].copy()

        # Variables exactas originales
        columnas_deuda = ["Mes", "SC", "SC (acum)", "TM", "IP", "AI"]
        cols_existentes = [
            col for col in columnas_deuda if col in df_tabla_deuda.columns
        ]

        if cols_existentes:
            # 3. Formatear la columna 'Mes' a MES-AAAA
            if (
                "Mes" in cols_existentes
                and "_Fecha_Temp" in df_tabla_deuda.columns
            ):
                df_tabla_deuda["Mes"] = df_tabla_deuda["_Fecha_Temp"].apply(
                    lambda dt: (
                        f"{NOMBRES_MESES.get(dt.month, '')}-{dt.year}"
                        if pd.notna(dt)
                        else ""
                    )
                )

            # 4. Formatear columnas numéricas (moneda y porcentaje)
            cols_moneda = [
                col for col in cols_existentes if col not in ["Mes", "TM"]
            ]

            for col in cols_moneda:
                df_tabla_deuda[col] = pd.to_numeric(
                    df_tabla_deuda[col], errors="coerce"
                ).fillna(0)
                df_tabla_deuda[col] = df_tabla_deuda[col].apply(
                    lambda x: f"${x:,.2f}"
                )

            if "TM" in cols_existentes:
                df_tabla_deuda["TM"] = pd.to_numeric(
                    df_tabla_deuda["TM"], errors="coerce"
                ).fillna(0)
                df_tabla_deuda["TM"] = df_tabla_deuda["TM"].apply(
                    lambda x: (
                        f"{x * 100:,.2f}%"
                        if 0 < x <= 1
                        else f"{x:,.2f}%"
                    )
                )

            st.dataframe(
                df_tabla_deuda[cols_existentes],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning(
                "No se encontraron las columnas especificadas en los datos de deuda."
            )
    else:
        st.warning("No hay datos disponibles para la línea de deuda.")