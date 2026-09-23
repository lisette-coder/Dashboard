import streamlit as st
import pandas as pd
import plotly.express as px
import calplot
import matplotlib.pyplot as plt
import calendar
import plotly.graph_objects as go
from plotly.subplots import make_subplots 

from .filtros import render_filtros_tiempo
from .constantes import meses_esp, dias_semana, dias_map



def render_curva_financiera_generica(
    df,
    columna_metrica,
    titulo_base,
    color_linea="royalblue",
    date_column="Fecha de Dispersión",
    filtro_estatus_col=None,
    filtro_estatus_val=None,
):
    """Plantilla única reutilizable para curvas temporales sencillas."""
    st.markdown("---")
    st.subheader(f"📈 {titulo_base}")

    df_trabajo = df.copy()
    if filtro_estatus_col and filtro_estatus_val:
        df_trabajo = df_trabajo[df_trabajo[filtro_estatus_col] == filtro_estatus_val]

    df_filtrado, tipo_filtro = render_filtros_tiempo(
        df_trabajo,
        sufijo_key=f"curva_{columna_metrica.lower().replace(' ', '_')}",
        date_column=date_column,
    )

    if date_column not in df_filtrado.columns:
        st.warning(
            f"No se encontró la columna de fecha '{date_column}' en los datos."
        )
        return

    if not df_filtrado.empty and columna_metrica in df_filtrado.columns:
        total_filtrado = df_filtrado[columna_metrica].sum()
        st.metric(
            label=f"Total Acumulado ({tipo_filtro})",
            value=f"${total_filtrado:,.2f}",
        )

    df_filtrado["Fecha_Dia"] = pd.to_datetime(
        df_filtrado[date_column], errors="coerce"
    ).dt.date
    df_agrupado = (
        df_filtrado.groupby("Fecha_Dia")[columna_metrica].sum().reset_index()
    )
    df_agrupado = df_agrupado.sort_values(by="Fecha_Dia")

    if not df_agrupado.empty:
        df_agrupado["Fecha_Str"] = pd.to_datetime(
            df_agrupado["Fecha_Dia"]
        ).dt.strftime("%Y-%m-%d")

        fig = px.line(
            df_agrupado,
            x="Fecha_Str",
            y=columna_metrica,
            markers=True,
            title=f"{titulo_base} ({tipo_filtro})",
            labels={"Fecha_Str": "Día", columna_metrica: f"{titulo_base} ($)"},
        )
        fig.update_traces(
            line=dict(width=2, color=color_linea),
            marker=dict(size=6),
            hovertemplate="Día: %{x}<br>Monto: $%{y:,.2f}<extra></extra>",
        )
        fig.update_layout(
            xaxis_title="Día",
            yaxis_title=f"{titulo_base} ($)",
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos diarios disponibles para el filtro seleccionado.")










def render_grafica_dispersiones_por_dia_semana(
    df, date_column="Fecha de Dispersión", monto_column="Monto Dispersado "
):
    """Genera barras agrupadas por día hábil ordenadas cronológicamente

    con una línea acumulada correcta.
    """
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
        st.warning(
            "No hay datos suficientes para generar la gráfica por días y semanas."
        )
        return

    # 1. Preparación y ordenamiento cronológico
    df_dia = df[[date_column, col_monto_real]].copy()
    df_dia["Fecha"] = pd.to_datetime(df_dia[date_column], errors="coerce")
    df_dia["Monto"] = pd.to_numeric(
        df_dia[col_monto_real], errors="coerce"
    ).fillna(0)
    df_dia = df_dia.dropna(subset=["Fecha"])

    if df_dia.empty:
        st.warning("No hay registros válidos para graficar.")
        return

    # Extraer variables temporales
    df_dia["Año"] = df_dia["Fecha"].dt.year
    df_dia["Num_Semana"] = df_dia["Fecha"].dt.isocalendar().week
    df_dia["Num_Dia"] = df_dia["Fecha"].dt.dayofweek

    # Filtrar solo Lunes a Viernes
    df_dia = df_dia[df_dia["Num_Dia"] <= 4]

    # Crear etiqueta de semana manteniendo el orden numérico
    df_dia["Semana_Etiqueta"] = df_dia["Num_Semana"].apply(
        lambda s: f"Semana {s:02d}"
    )

    dias_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes"}
    df_dia["Día"] = df_dia["Num_Dia"].map(dias_map)

    # 2. Agrupar ordenando primero por Año y Número de Semana
    df_grouped = (
        df_dia.groupby(["Año", "Num_Semana", "Semana_Etiqueta", "Num_Dia", "Día"])[
            "Monto"
        ]
        .sum()
        .reset_index()
    )

    # Orden estricto cronológico
    df_grouped = df_grouped.sort_values(by=["Año", "Num_Semana", "Num_Dia"])

    # Calcular acumulado ordenado
    df_grouped["Acumulado"] = df_grouped["Monto"].cumsum()

    # Obtener orden único de semanas para el eje X
    semanas_ordenadas = list(df_grouped["Semana_Etiqueta"].unique())

    # Paleta de colores para los 5 días
    colores_dias = {
        "Lunes": "#90e0ef",
        "Martes": "#48cae4",
        "Miércoles": "#0096c7",
        "Jueves": "#03045e",
        "Viernes": "#023e8a",
    }

    # 3. Construir la gráfica de Plotly
    fig = go.Figure()

    # Trazos de barras por día
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

    # Agrupar el acumulado por semana para la línea continua única
    df_linea = (
        df_grouped.groupby(["Año", "Num_Semana", "Semana_Etiqueta"])["Acumulado"]
        .max()
        .reset_index()
    )
    df_linea = df_linea.sort_values(by=["Año", "Num_Semana"])

    # Trazo único de la línea acumulada
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

    # 4. Configurar Layout
    fig.update_layout(
        barmode="group",
        bargap=0.20,
        bargroupgap=0.05,
        title="Distribución Diaria por Semana y Curva Acumulativa",
        xaxis=dict(
            title="Semana del Año",
            type="category",
            categoryorder="array",
            categoryarray=semanas_ordenadas,  # Forzar el orden cronológico estricto
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
    monto_column="Monto Dispersado ",
):
    """Genera un calendario de calor anual compacto con casillas cuadradas y semanas ordenadas correctamente."""
    st.markdown("### 📅 Calendario Anual de Dispersiones")

    # Limpieza de nombre de columna por seguridad
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

    # 1. Preparación de datos
    df_heat = df[[date_column, col_monto_real]].copy()
    df_heat["Fecha"] = pd.to_datetime(df_heat[date_column], errors="coerce")
    df_heat["Monto"] = pd.to_numeric(
        df_heat[col_monto_real], errors="coerce"
    ).fillna(0)
    df_heat = df_heat.dropna(subset=["Fecha"])

    if df_heat.empty:
        st.warning("No hay fechas válidas en los datos.")
        return

    # Determinar el año a mostrar (el más reciente en el dataset)
    anio = int(df_heat["Fecha"].dt.year.max())

    # Agrupar suma por fecha exacta (YYYY-MM-DD)
    df_daily = (
        df_heat.groupby(df_heat["Fecha"].dt.strftime("%Y-%m-%d"))["Monto"]
        .sum()
        .to_dict()
    )

    

    # 2. Configurar cuadrícula Subplots 3 filas x 4 columnas
    fig = make_subplots(
        rows=3,
        cols=4,
        subplot_titles=meses_esp,
        vertical_spacing=0.07,
        horizontal_spacing=0.03,
    )

    # Buscar el valor máximo global para normalizar la escala de color
    max_monto = max(df_daily.values()) if df_daily else 1

    # Paleta de colores: Azul Marino -> Acua -> Turquesa claro
    custom_blues = [
        [0.0, "#f0f8ff"],  # Blanco/Azul helado (Días sin dispersión)
        [0.001, "#b2ebd9"],  # Acua claro (Monto muy bajo)
        [0.35, "#4682b4"],  # Azul Acero
        [0.70, "#005f73"],  # Azul Petróleo
        [1.0, "#0a2540"],  # Azul Marino Intenso (Picos máximos)
    ]

    # 3. Construir el calendario mes a mes
    calendar.setfirstweekday(calendar.SUNDAY)  # Iniciar semanas en Domingo

    for mes in range(1, 13):
        row = (mes - 1) // 4 + 1
        col = (mes - 1) % 4 + 1

        cal = calendar.monthcalendar(anio, mes)

        z_vals = []  # Valores numéricos para el color
        text_vals = []  # Número del día para la casilla
        hover_vals = []  # Texto al pasar el cursor

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

        # NOTA: Se removieron los .reverse() para evitar invertir dos veces el eje Y

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

        # Ocultar eje Y en todos los subplots
        fig.update_yaxes(visible=False, row=row, col=col)

        # Configurar eje X: Mostrar días SOLO en la última fila (row == 3)
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

    # 4. Forzar que las casillas se mantengan cuadradas (relación 1:1) e invertir eje Y aquí
    for r in range(1, 4):
        for c in range(1, 5):
            idx = (r - 1) * 4 + c
            axis_suffix = "" if idx == 1 else str(idx)
            fig.update_layout(
                {
                    f"yaxis{axis_suffix}": dict(
                        scaleanchor=f"x{axis_suffix}",
                        scaleratio=1,
                        autorange="reversed",  # Invierte el eje Y para que la fila 0 (día 1) quede arriba
                    )
                }
            )

    # Layout general
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