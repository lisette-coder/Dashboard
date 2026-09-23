import streamlit as st
import pandas as pd
import plotly.express as px

from .filtros import render_filtros_tiempo


def render_curva_clientes_activos_diarios(
    df, date_column="Fecha de Dispersión", columna_cliente="RFC Proveedor"
):
    """Renderiza actividad diaria, ticket promedio y conteo de clientes únicos."""
    st.markdown("---")
    st.subheader("📈 Actividad de Clientes y Dispersiones por Día")

    if date_column not in df.columns or columna_cliente not in df.columns:
        st.warning(
            f"Faltan columnas necesarias ('{date_column}' o '{columna_cliente}') en los datos."
        )
        return

    df_filtrado, tipo_filtro = render_filtros_tiempo(
        df, sufijo_key="clientes_activos_diarios", date_column=date_column
    )

    if df_filtrado.empty:
        st.warning("No hay datos disponibles para el filtro seleccionado.")
        return

    total_clientes_unicos = df_filtrado[columna_cliente].nunique()
    total_facturas = len(df_filtrado)

    col_monto_ticket = (
        "Monto Dispersado"
        if "Monto Dispersado" in df_filtrado.columns
        else (
            "Monto a Recibir"
            if "Monto a Recibir" in df_filtrado.columns
            else None
        )
    )

    ticket_promedio = (
        (df_filtrado[col_monto_ticket].sum() / total_facturas)
        if (col_monto_ticket and total_facturas > 0)
        else 0.0
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label=f"Clientes Únicos ({tipo_filtro})",
            value=f"{total_clientes_unicos:,}",
        )
    with col2:
        st.metric(
            label=f"Facturas ({tipo_filtro})",
            value=f"{total_facturas:,}",
        )
    with col3:
        st.metric(
            label=f"Ticket Promedio ({tipo_filtro})",
            value=f"${ticket_promedio:,.2f}",
        )

    df_filtrado["Fecha_Dia"] = pd.to_datetime(
        df_filtrado[date_column], errors="coerce"
    ).dt.date
    df_agrupado = (
        df_filtrado.groupby("Fecha_Dia")[columna_cliente]
        .nunique()
        .reset_index()
    )
    df_agrupado = df_agrupado.rename(
        columns={columna_cliente: "Cantidad_Clientes"}
    ).dropna(subset=["Fecha_Dia"])
    df_agrupado = df_agrupado.sort_values(by="Fecha_Dia")

    if not df_agrupado.empty:
        df_agrupado["Fecha_Str"] = pd.to_datetime(
            df_agrupado["Fecha_Dia"]
        ).dt.strftime("%Y-%m-%d")

        fig = px.line(
            df_agrupado,
            x="Fecha_Str",
            y="Cantidad_Clientes",
            markers=True,
            title=f"Evolución Diaria de Clientes Activos ({tipo_filtro})",
            labels={
                "Fecha_Str": "Día",
                "Cantidad_Clientes": "Número de Clientes",
            },
            color_discrete_sequence=["#FF1493"],
        )
        fig.update_traces(
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate="Día: %{x}<br>Clientes operando: %{y:,}<extra></extra>",
        )
        fig.update_layout(
            xaxis_title="Día",
            yaxis_title="Clientes Únicos",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos diarios de clientes para mostrar en este rango.")
