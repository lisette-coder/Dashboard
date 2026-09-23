from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from .constantes import NOMBRES_MESES


def render_curva_revenue_vs_intereses(
    df_consolidado,
    df_deuda,
    date_column_conv="Fecha de Dispersión",
    date_column_deuda="Mes",
):
    """Renderiza de forma global la comparativa de Revenue vs Intereses de Deuda."""
    st.markdown("---")
    st.subheader(
        "📈 Evolución y Análisis: Revenue Kamina vs. Intereses Cobrados"
    )

    if df_consolidado is None or df_consolidado.empty:
        st.warning("Faltan datos en el consolidado para generar la vista.")
        return

    total_capital_fondeo = 0.0
    if (
        df_deuda is not None
        and not df_deuda.empty
        and "SC" in df_deuda.columns
    ):
        total_capital_fondeo = (
            pd.to_numeric(df_deuda["SC"], errors="coerce").fillna(0).sum()
        )

    col_pago_kamina = "Monto a Pagar a Kamina"
    col_estatus_pago = "Estatus Pago a Kamina"
    capital_en_calle_tobepaid = 0.0

    if (
        col_pago_kamina in df_consolidado.columns
        and col_estatus_pago in df_consolidado.columns
    ):
        mask_tobepaid = (
            df_consolidado[col_estatus_pago].astype(str).str.strip()
            == "To be paid"
        )
        capital_en_calle_tobepaid = (
            pd.to_numeric(
                df_consolidado.loc[mask_tobepaid, col_pago_kamina],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

    capital_recuperado_paid = total_capital_fondeo - capital_en_calle_tobepaid

    col1, col2, col3 = st.columns(3)
    col1.metric("Capital / Fondeo Total", f"${total_capital_fondeo:,.2f}")
    col2.metric("Capital en uso", f"${capital_en_calle_tobepaid:,.2f}")
    col3.metric(
        "Capital disponible",
        f"${capital_recuperado_paid:,.2f}",
        delta_color="off",
    )

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

    # --- SECCIÓN TABLA DETALLE DE DEUDA ---
    st.markdown("### 📋 Detalle de Línea de Deuda")

    if df_deuda is not None and not df_deuda.empty:
        df_tabla_deuda = df_deuda.copy()

        # 1. Asegurar formato datetime para filtrar y formatear
        if "Mes" in df_tabla_deuda.columns:
            df_tabla_deuda["_Fecha_Temp"] = pd.to_datetime(
                df_tabla_deuda["Mes"], errors="coerce"
            )

            # 2. Filtrar solo los registros hasta el mes actual
            hoy = datetime.now()
            primer_dia_mes_siguiente = (
                datetime(hoy.year, hoy.month + 1, 1)
                if hoy.month < 12
                else datetime(hoy.year + 1, 1, 1)
            )

            df_tabla_deuda = df_tabla_deuda[
                df_tabla_deuda["_Fecha_Temp"] < primer_dia_mes_siguiente
            ].copy()

        columnas_deuda = [
            "Mes",
            "SC",
            "SC (acum)",
            "TM",
            "IP",
            "AI",
        ]

        # Seleccionar únicamente las columnas que existan
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

            # 4. Formatear columnas numéricas
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

            # Renderizar tabla final
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