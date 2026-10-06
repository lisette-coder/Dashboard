import calendar
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime

from .constantes import dias_map, dias_semana, meses_esp
from .filtros import render_filtros_tiempo


def _limpiar_a_float(val):
    """Limpia cadenas con '$', ',' o espacios y devuelve float seguro."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).replace("$", "").replace(",", "").strip()
    return pd.to_numeric(val_str, errors="coerce") or 0.0


def render_curva_financiera_generica(
    df,
    columna_metrica="Monto Dispersado",
    titulo_base="Evolución de Montos Dispersados",
    color_linea="royalblue",
    date_column="Fecha de Dispersión",
    filtro_estatus_col=None,
    filtro_estatus_val=None,
):
    """Suma y muestra la evolución diaria de montos dispersados por fecha de dispersión."""
    st.markdown("---")
    st.subheader(f"📈 {titulo_base}")

    df_trabajo = df.copy()

    # Normalizar nombre de columna de monto por si tiene espacios residuales
    col_monto = (
        columna_metrica
        if columna_metrica in df_trabajo.columns
        else columna_metrica.strip()
    )

    if (
        date_column not in df_trabajo.columns
        or col_monto not in df_trabajo.columns
    ):
        st.warning(
            f"No se encontraron las columnas necesarias ('{date_column}' / '{col_monto}') en los datos."
        )
        return

    if filtro_estatus_col and filtro_estatus_val:
        df_trabajo = df_trabajo[
            df_trabajo[filtro_estatus_col] == filtro_estatus_val
        ]

    # Convertir a datetime y filtrar para evitar mostrar fechas futuras a la de hoy
    df_trabajo["_Fecha_DT"] = pd.to_datetime(
        df_trabajo[date_column], errors="coerce"
    )
    hoy = datetime.now()
    df_trabajo = df_trabajo[df_trabajo["_Fecha_DT"] <= hoy].copy()

    df_filtrado, tipo_filtro = render_filtros_tiempo(
        df_trabajo,
        sufijo_key=f"curva_{col_monto.lower().replace(' ', '_')}",
        date_column=date_column,
    )

    if not df_filtrado.empty:
        df_filtrado["Monto_Num"] = df_filtrado[col_monto].apply(_limpiar_a_float)
        df_filtrado["Fecha_Dia"] = pd.to_datetime(
            df_filtrado[date_column], errors="coerce"
        ).dt.date

        total_filtrado = df_filtrado["Monto_Num"].sum()

        st.metric(
            label=f"Total Acumulado Dispersado ({tipo_filtro})",
            value=f"${total_filtrado:,.2f}",
        )

        # Suma exacta de montos por cada día de dispersión
        df_agrupado = (
            df_filtrado.groupby("Fecha_Dia")["Monto_Num"].sum().reset_index()
        )
        df_agrupado = df_agrupado.sort_values(by="Fecha_Dia")

        if not df_agrupado.empty:
            df_agrupado["Fecha_Str"] = pd.to_datetime(
                df_agrupado["Fecha_Dia"]
            ).dt.strftime("%Y-%m-%d")

            fig = px.line(
                df_agrupado,
                x="Fecha_Str",
                y="Monto_Num",
                markers=True,
                title=f"{titulo_base} - Vista Diaria ({tipo_filtro})",
                labels={"Fecha_Str": "Día", "Monto_Num": "Monto Dispersado ($)"},
            )
            fig.update_traces(
                line=dict(width=2, color=color_linea),
                marker=dict(size=6),
                hovertemplate="Día: %{x}<br>Monto Dispersado: $%{y:,.2f}<extra></extra>",
            )
            fig.update_layout(
                xaxis_title="Día",
                yaxis_title="Monto Dispersado ($)",
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos diarios disponibles para el filtro seleccionado.")
    else:
        st.warning("No hay registros en el rango seleccionado.")


def render_grafica_dispersiones_por_dia_semana(
    df, date_column="Fecha de Dispersión", monto_column="Monto Dispersado"
):
    """Genera barras agrupadas por día hábil con curva acumulada."""
    st.markdown("### 📊 Dispersión Diaria Agrupada por Semana")

    col_monto_real = (
        monto_column if monto_column in df.columns else monto_column.strip()
    )

    if (
        df is None
        or df.empty
        or date_column not in df.columns
        or col_monto_real not in df.columns
    ):
        st.warning("No hay datos suficientes para generar la gráfica por días y semanas.")
        return

    df_dia = df[[date_column, col_monto_real]].copy()
    df_dia["Fecha"] = pd.to_datetime(df_dia[date_column], errors="coerce")
    
    # Filtrar fechas mayores al día de hoy
    hoy = datetime.now()
    df_dia = df_dia[df_dia["Fecha"] <= hoy]

    df_dia["Monto"] = df_dia[col_monto_real].apply(_limpiar_a_float)
    df_dia = df_dia.dropna(subset=["Fecha"])

    if df_dia.empty:
        st.warning("No hay registros válidos para graficar.")
        return

    df_dia["Año"] = df_dia["Fecha"].dt.year
    df_dia["Num_Semana"] = df_dia["Fecha"].dt.isocalendar().week
    df_dia["Num_Dia"] = df_dia["Fecha"].dt.dayofweek

    # Solo Lunes a Viernes
    df_dia = df_dia[df_dia["Num_Dia"] <= 4]

    df_dia["Semana_Etiqueta"] = df_dia["Num_Semana"].apply(lambda s: f"Semana {s:02d}")
    dias_map_local = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes"}
    df_dia["Día"] = df_dia["Num_Dia"].map(dias_map_local)

    df_grouped = (
        df_dia.groupby(["Año", "Num_Semana", "Semana_Etiqueta", "Num_Dia", "Día"])[
            "Monto"
        ]
        .sum()
        .reset_index()
    )

    df_grouped = df_grouped.sort_values(by=["Año", "Num_Semana", "Num_Dia"])
    df_grouped["Acumulado"] = df_grouped["Monto"].cumsum()

    semanas_ordenadas = list(df_grouped["Semana_Etiqueta"].unique())

    colores_dias = {
        "Lunes": "#90e0ef",
        "Martes": "#48cae4",
        "Miércoles": "#0096c7",
        "Jueves": "#03045e",
        "Viernes": "#023e8a",
    }

    fig = go.Figure()

    for dia_nombre in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]:
        df_sub = df_grouped[df_grouped["Día"] == dia_nombre]
        fig.add_trace(
            go.Bar(
                x=df_sub["Semana_Etiqueta"],
                y=df_sub["Monto"],
                name=dia_nombre,
                marker_color=colores_dias[dia_nombre],
                hovertemplate=f"<b>{dia_nombre} - %{{x}}</b><br>Dispersado: $%{{y:,.2f}}<extra></extra>",
            )
        )

    df_linea = (
        df_grouped.groupby(["Año", "Num_Semana", "Semana_Etiqueta"])["Acumulado"]
        .max()
        .reset_index()
    )
    df_linea = df_linea.sort_values(by=["Año", "Num_Semana"])

    fig.add_trace(
        go.Scatter(
            x=df_linea["Semana_Etiqueta"],
            y=df_linea["Acumulado"],
            name="Monto Acumulado",
            mode="lines+markers",
            line=dict(color='#93c572', width=2.5),
            marker=dict(size=6, color="#93c572"),
            yaxis="y2",
            hovertemplate="<b>Acumulado en %{x}:</b> $%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="group",
        bargap=0.20,
        bargroupgap=0.05,
        title="Distribución Diaria por Semana y Curva Acumulativa",
        xaxis=dict(
            title="Semana del Año",
            type="category",
            categoryorder="array",
            categoryarray=semanas_ordenadas,
        ),
        yaxis=dict(
            title="Monto Dispersado por Día ($)",
            tickprefix="$",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
        ),
        yaxis2=dict(
            title="Monto Acumulado ($)",
            tickprefix="$",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
        ),
        height=480,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_calendario_calor_dispersiones(
    df,
    date_column="Fecha de Dispersión",
    monto_column="Monto Dispersado",
):
    """Genera un calendario de calor anual basado en la Fecha de Dispersión."""
    st.markdown("### 📅 Calendario Anual de Dispersiones")

    col_monto_real = (
        monto_column if monto_column in df.columns else monto_column.strip()
    )

    if (
        df is None
        or df.empty
        or date_column not in df.columns
        or col_monto_real not in df.columns
    ):
        st.warning("No hay datos suficientes para generar el calendario.")
        return

    df_heat = df[[date_column, col_monto_real]].copy()
    df_heat["Fecha"] = pd.to_datetime(df_heat[date_column], errors="coerce")

    # Filtrar fechas mayores al día de hoy
    hoy = datetime.now()
    df_heat = df_heat[df_heat["Fecha"] <= hoy]

    df_heat["Monto"] = df_heat[col_monto_real].apply(_limpiar_a_float)
    df_heat = df_heat.dropna(subset=["Fecha"])

    if df_heat.empty:
        st.warning("No hay fechas válidas en los datos.")
        return

    anio = int(df_heat["Fecha"].dt.year.max())

    df_daily = (
        df_heat.groupby(df_heat["Fecha"].dt.strftime("%Y-%m-%d"))["Monto"]
        .sum()
        .to_dict()
    )

    fig = make_subplots(
        rows=3,
        cols=4,
        subplot_titles=meses_esp,
        vertical_spacing=0.07,
        horizontal_spacing=0.03,
    )

    max_monto = max(df_daily.values()) if df_daily else 1

    custom_blues = [
        [0.0, "#f0f8ff"],
        [0.001, "#b2ebd9"],
        [0.35, "#4682b4"],
        [0.70, "#005f73"],
        [1.0, "#0a2540"],
    ]

    calendar.setfirstweekday(calendar.SUNDAY)

    for mes in range(1, 13):
        row = (mes - 1) // 4 + 1
        col = (mes - 1) % 4 + 1

        cal = calendar.monthcalendar(anio, mes)

        z_vals = []
        text_vals = []
        hover_vals = []

        for semana in cal:
            fila_z = []
            fila_text = []
            fila_hover = []

            for dia in semana:
                if dia == 0:
                    fila_z.append(None)
                    fila_text.append("")
                    fila_hover.append("")
                else:
                    fecha_str = f"{anio}-{mes:02d}-{dia:02d}"
                    monto = df_daily.get(fecha_str, 0)
                    fila_z.append(monto)
                    fila_text.append(str(dia))
                    fila_hover.append(
                        f"Fecha: {fecha_str}<br>Dispersado: ${monto:,.2f}"
                    )

            z_vals.append(fila_z)
            text_vals.append(fila_text)
            hover_vals.append(fila_hover)

        heatmap = go.Heatmap(
            z=z_vals,
            x=dias_semana,
            text=text_vals,
            texttemplate="%{text}",
            hovertext=hover_vals,
            hoverinfo="text",
            colorscale=custom_blues,
            zmin=0,
            zmax=max_monto,
            showscale=False,
            xgap=2,
            ygap=2,
        )

        fig.add_trace(heatmap, row=row, col=col)
        fig.update_yaxes(visible=False, row=row, col=col)

        es_ultima_fila = row == 3
        fig.update_xaxes(
            showline=False,
            showgrid=False,
            zeroline=False,
            showticklabels=es_ultima_fila,
            side="bottom",
            tickfont=dict(size=8),
            row=row,
            col=col,
        )

    for r in range(1, 4):
        for c in range(1, 5):
            idx = (r - 1) * 4 + c
            axis_suffix = "" if idx == 1 else str(idx)
            fig.update_layout(
                {
                    f"yaxis{axis_suffix}": dict(
                        scaleanchor=f"x{axis_suffix}",
                        scaleratio=1,
                        autorange="reversed",
                    )
                }
            )

    fig.update_layout(
        title=dict(
            text=f"Resumen Anual de Dispersiones {anio}",
            x=0.5,
            xanchor="center",
            font=dict(size=16),
        ),
        height=480,
        margin=dict(l=10, r=10, t=50, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)