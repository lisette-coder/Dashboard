import calendar
from datetime import datetime
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .constantes import NOMBRES_MESES


def _limpiar_a_float(val):
    """Convierte de forma segura textos como '$10,936.80' a float."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    # Eliminar $, comas, % y espacios
    val_str = (
        str(val).replace("$", "").replace(",", "").replace("%", "").strip()
    )

    num = pd.to_numeric(val_str, errors="coerce")
    return float(num) if pd.notna(num) else 0.0


def render_tarjetas_kpi(
    df,
    df_deuda=None,
    columna_monto="Monto a Pagar a Kamina",  # Columna principal solicitada
    columna_estatus="Estatus Pago a Kamina",
    tipo_filtro="Período Seleccionado",
    anio_kpi=None,
    mes_kpi=None,
):
    """Calcula y muestra el bloque de 4 tarjetas KPI principales en formato vertical."""
    if df is None or df.empty:
        st.warning("No hay datos disponibles para mostrar las tarjetas.")
        return

    hoy = datetime.now()
    anio_kpi = anio_kpi if anio_kpi is not None else hoy.year
    mes_kpi = mes_kpi if mes_kpi is not None else hoy.month

    df_copy = df.copy()
    df_copy.columns = df_copy.columns.str.strip()

    # Identificación flexible de la columna de Monto a Pagar a Kamina
    col_monto_kamina = next(
        (
            c
            for c in df_copy.columns
            if c.lower().strip() == columna_monto.lower().strip()
            or "monto a pagar a kamina" in c.lower()
        ),
        columna_monto,
    )

    # Identificación flexible de la columna de Estatus
    col_estatus_kamina = next(
        (
            c
            for c in df_copy.columns
            if c.lower().strip() == columna_estatus.lower().strip()
            or "estatus pago" in c.lower()
        ),
        columna_estatus,
    )

    # -------------------------------------------------------------------------
    # 1. ADELANTOS LIQUIDADOS: "Monto a Pagar a Kamina" donde Estatus == "PAID"
    # -------------------------------------------------------------------------
    monto_liquidados = 0.0
    if col_estatus_kamina in df_copy.columns and col_monto_kamina in df_copy.columns:
        mask_paid = (
            df_copy[col_estatus_kamina].astype(str).str.strip().str.upper()
            == "PAID"
        )
        monto_liquidados = (
            df_copy.loc[mask_paid, col_monto_kamina]
            .apply(_limpiar_a_float)
            .sum()
        )

    # -------------------------------------------------------------------------
    # 2. CAPITAL EN USO: "Monto a Pagar a Kamina" donde Estatus == "To be paid"
    # -------------------------------------------------------------------------
    capital_en_uso = 0.0
    if col_estatus_kamina in df_copy.columns and col_monto_kamina in df_copy.columns:
        mask_tobepaid = (
            df_copy[col_estatus_kamina].astype(str).str.strip().str.lower()
            == "to be paid"
        )
        capital_en_uso = (
            df_copy.loc[mask_tobepaid, col_monto_kamina]
            .apply(_limpiar_a_float)
            .sum()
        )

    # -------------------------------------------------------------------------
    # 3. CAPITAL / FONDEO TOTAL: Valor positivo de "SC (acum)"
    # -------------------------------------------------------------------------
    total_capital_fondeo = 0.0
    if df_deuda is not None and not df_deuda.empty:
        df_d = df_deuda.copy()
        df_d.columns = df_d.columns.str.strip()

        if "SC (acum)" in df_d.columns:
            serie_sc = df_d["SC (acum)"].apply(_limpiar_a_float)
            serie_positiva = serie_sc[serie_sc > 0]
            if not serie_positiva.empty:
                total_capital_fondeo = serie_positiva.iloc[-1]

    # -------------------------------------------------------------------------
    # 4. CAPITAL DISPONIBLE: Resta (Fondeo Total - Capital en Uso)
    # -------------------------------------------------------------------------
    capital_disponible = max(0.0, total_capital_fondeo - capital_en_uso)

    # RENDERIZADO EN PANTALLA
    st.markdown("### ✨ Insights del periodo")

    with st.container(border=True):
        st.caption(f"💼 Adelantos Liquidados")
        st.subheader(f"${monto_liquidados:,.2f}")
        st.caption("Monto total liquidado en el período.")

    with st.container(border=True):
        st.caption("💳 Capital en uso")
        st.subheader(f"${capital_en_uso:,.2f}")
        st.caption("Monto asignado listo o pendiente de cobro.")

    with st.container(border=True):
        st.caption("🏛️ Capital / Fondeo Total")
        st.subheader(f"${total_capital_fondeo:,.2f}")
        st.caption("Total de fondeo acumulado (SC).")

    with st.container(border=True):
        st.caption("🟢 Capital disponible")
        st.subheader(f"${capital_disponible:,.2f}")
        st.caption("Listo para nuevas operaciones.")




def render_curva_cartera_dual(
    df,
    columna_metrica="Monto a Pagar a Kamina",
    titulo_base="Evolución de Cartera Dual",
    date_column="Fecha Vencimiento",
    tipo_filtro="Año Completo",
):
    """Renderiza el gráfico diario de PAID vs To be paid."""

    st.markdown("---")
    st.subheader(f"📈 {titulo_base}")

    columnas_necesarias = [
        date_column,
        "Estatus Pago a Kamina",
        columna_metrica,
    ]

    if df is None or df.empty:
        st.warning("No hay datos disponibles para generar la gráfica.")
        return

    columnas_faltantes = [
        col for col in columnas_necesarias if col not in df.columns
    ]

    if columnas_faltantes:
        st.warning(
            f"Faltan columnas necesarias: {', '.join(columnas_faltantes)}"
        )
        return

    df = df.copy()

    df["Estatus Pago a Kamina"] = df["Estatus Pago a Kamina"].astype(str).str.strip()

    df[date_column] = pd.to_datetime(
        df[date_column],
        errors="coerce",
        dayfirst=True,
    )

    df["Fecha_Dia"] = df[date_column].dt.normalize()

    df[columna_metrica] = (
        df[columna_metrica]
        .astype(str)
        .str.strip()
        .str.replace("$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", "", regex=False)
    )

    df[columna_metrica] = pd.to_numeric(df[columna_metrica], errors="coerce")

    df = df.dropna(subset=["Fecha_Dia", columna_metrica])

    df_pendiente = df[
        df["Estatus Pago a Kamina"].str.lower() == "to be paid"
    ].copy()

    df_pagado = df[df["Estatus Pago a Kamina"].str.upper() == "PAID"].copy()

    df_pend_grouped = (
        df_pendiente.groupby("Fecha_Dia", as_index=False)[columna_metrica].sum()
    )
    df_pend_grouped["Tipo_Flujo"] = "Pendiente / Por Pagar"

    df_pag_grouped = (
        df_pagado.groupby("Fecha_Dia", as_index=False)[columna_metrica].sum()
    )
    df_pag_grouped["Tipo_Flujo"] = "Pagado / Liquidado"

    df_final = pd.concat([df_pag_grouped, df_pend_grouped], ignore_index=True)

    df_final = df_final.dropna(subset=["Fecha_Dia"])

    df_final = df_final.sort_values(["Tipo_Flujo", "Fecha_Dia"]).reset_index(
        drop=True
    )

    if df_final.empty:
        st.warning(
            "No hay datos diarios disponibles para graficar en este rango."
        )
        return

    fig = px.line(
        df_final,
        x="Fecha_Dia",
        y=columna_metrica,
        color="Tipo_Flujo",
        markers=True,
        title=f"{titulo_base} - Vista Diaria ({tipo_filtro})",
        labels={
            "Fecha_Dia": "Día",
            columna_metrica: f"{titulo_base} ($)",
            "Tipo_Flujo": "Flujo",
        },
        color_discrete_map={
            "Pendiente / Por Pagar": "darkorange",
            "Pagado / Liquidado": "forestgreen",
        },
    )

    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=6),
        hovertemplate=(
            "Día: %{x|%d/%m/%Y}<br>Monto: $%{y:,.2f}<extra></extra>"
        ),
    )

    fig.update_layout(
        xaxis_title="Día",
        yaxis_title=f"{titulo_base} ($)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=-45,
        legend_title="Flujo",
    )

    fig.update_xaxes(
        type="date",
        tickformat="%b %Y",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_dona_composicion_capital(
    df,
    df_deuda,
    columna_metrica="Monto a Pagar a Kamina",  # Columna Z en tu Google Sheet
    columna_estatus="Estatus Pago a Kamina",  # Columna AA en tu Google Sheet
    columna_deuda_sc="SC (acum)",
    columna_mes="Mes",
):
    """Genera el gráfico de dona compuesto por Capital Colocado y Capital Disponible."""
    st.markdown("### 🍩 Composición del Capital")

    if df is None or df.empty or df_deuda is None or df_deuda.empty:
        st.warning("No hay datos suficientes para calcular la composición.")
        return

    df_c = df.copy()
    df_d = df_deuda.copy()

    df_c.columns = df_c.columns.str.strip()
    df_d.columns = df_d.columns.str.strip()

    # Intercambiar DataFrames si vienen invertidos
    if (
        columna_deuda_sc in df_c.columns
        and columna_deuda_sc not in df_d.columns
    ):
        df_c, df_d = df_d, df_c

    # Fallback si la columna ingresada no existe
    if columna_metrica not in df_c.columns:
        if "Monto Dispersado" in df_c.columns:
            columna_metrica = "Monto Dispersado"
        elif "Monto a Pagar a Kamina" in df_c.columns:
            columna_metrica = "Monto a Pagar a Kamina"

    if (
        columna_deuda_sc not in df_d.columns
        or columna_metrica not in df_c.columns
        or columna_estatus not in df_c.columns
    ):
        st.warning(
            f"Faltan columnas requeridas para el gráfico de dona. (Buscadas: '{columna_metrica}', '{columna_estatus}', '{columna_deuda_sc}')"
        )
        return

    # --- 1. OBTENER CAPITAL TOTAL DESDE LA HOJA DE DEUDA ---
    serie_sc = df_d[columna_deuda_sc].apply(_limpiar_a_float)
    serie_positiva = serie_sc[serie_sc > 0]
    capital_total = serie_positiva.iloc[-1] if not serie_positiva.empty else 0.0

    # --- 2. CÁLCULO DE CAPITAL EN USO ("To be paid") ---
    # Normalizar texto para evitar fallos por espacios o diferencias de mayúsculas/minúsculas
    estatus_normalizado = (
        df_c[columna_estatus].astype(str).str.strip().str.lower()
    )
    mask_tbp = estatus_normalizado == "to be paid"

    capital_en_uso = (
        df_c.loc[mask_tbp, columna_metrica].apply(_limpiar_a_float).sum()
    )

    # --- 3. CÁLCULO DE CAPITAL DISPONIBLE ---
    disponible = max(0.0, capital_total - capital_en_uso)

    labels = ["Capital Disponible", "Capital en Uso (Colocado)"]
    values = [disponible, capital_en_uso]
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



def _limpiar_a_float(val):
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


def render_barras_colocado_mensual(
    df, date_column="Fecha de Dispersión", monto_column="Monto Dispersado"
):
    """Genera el gráfico de barras del monto colocado por mes aprovechando las columnas Día, Mes y Año."""
    st.markdown("### 📊 Capital Colocado por Mes")

    if df is None or df.empty:
        st.warning("No hay datos suficientes.")
        return

    df_temp = df.copy()

    # 1. Limpieza estricta de la columna de Monto
    col_monto = (
        monto_column if monto_column in df.columns else "Monto Dispersado"
    )
    df_temp["Monto_Limpio"] = df_temp[col_monto].apply(_limpiar_a_float)

    # 2. Reconstrucción segura de Fecha desde las columnas Día, Mes y Año de tu Google Sheet
    if (
        "Día" in df_temp.columns
        and "Mes" in df_temp.columns
        and "Año" in df_temp.columns
    ):
        df_temp["Año_num"] = pd.to_numeric(df_temp["Año"], errors="coerce")
        df_temp["Mes_num"] = pd.to_numeric(df_temp["Mes"], errors="coerce")
        df_temp["Dia_num"] = pd.to_numeric(df_temp["Día"], errors="coerce")

        # Crear fecha real sin fallas de formato DD/MM vs MM/DD
        df_temp["Fecha_Clean"] = pd.to_datetime(
            dict(
                year=df_temp["Año_num"],
                month=df_temp["Mes_num"],
                day=df_temp["Dia_num"],
            ),
            errors="coerce",
        )
    else:
        # Fallback a la columna Fecha de Dispersión especificando formato estricto
        df_temp["Fecha_Clean"] = pd.to_datetime(
            df_temp[date_column].astype(str).str.strip(),
            format="%d/%m/%Y",
            errors="coerce",
        )

    # Filtrar solo registros donde la fecha se reconstruyó bien
    df_temp = df_temp.dropna(subset=["Fecha_Clean"])

    # 3. Extraer Año y Mes
    df_temp["Año_Val"] = df_temp["Fecha_Clean"].dt.year
    df_temp["Mes_Val"] = df_temp["Fecha_Clean"].dt.month

    # 4. Agrupar y Sumar TODO el monto sin descartar filas
    df_mensual = (
        df_temp.groupby(["Año_Val", "Mes_Val"], as_index=False)["Monto_Limpio"]
        .sum()
        .sort_values(by=["Año_Val", "Mes_Val"])
    )

    df_mensual["Mes_Nombre"] = (
        df_mensual["Mes_Val"].map(NOMBRES_MESES)
        + " "
        + df_mensual["Año_Val"].astype(str)
    )

    # 5. Dibujar la Gráfica
    fig = go.Figure(
        go.Bar(
            x=df_mensual["Monto_Limpio"],
            y=df_mensual["Mes_Nombre"],
            orientation="h",
            marker=dict(
                color=df_mensual["Monto_Limpio"],
                colorscale="Blues",
                showscale=False,
            ),
            text=[f"${m:,.2f}" for m in df_mensual["Monto_Limpio"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Monto Dispersado: $%{x:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            title="",
        ),
        yaxis=dict(showgrid=False, autorange="reversed"),
        height=380,
        margin=dict(l=10, r=120, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)





def _limpiar_a_float(val):
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


def render_seccion_cartera(df=None):
    if df is None:
        from utils import load_data_consolidado

        df = load_data_consolidado()

    if df is None or df.empty:
        st.warning("No hay datos disponibles para la sección de Cartera.")
        return

    df_cartera = df.copy()
    df_cartera.columns = df_cartera.columns.str.strip()

    # Nombres de columnas
    col_retraso = "Dias de retraso"
    col_interes = "Interes acumulado"
    col_monto = "Monto Liquidado"
    col_fecha_venc = (
        "Fecha de Vencimiento"
        if "Fecha de Vencimiento" in df_cartera.columns
        else "Fecha de Liquidación"
    )
    col_fecha_disp = (
        "Fecha de Dispersión"
        if "Fecha de Dispersión" in df_cartera.columns
        else "Fecha de Liquidación"
    )
    col_estatus = (
        "Estatus Pago a Kamina"
        if "Estatus Pago a Kamina" in df_cartera.columns
        else "Estatus"
    )

    # Convertir columnas numéricas
    for col in [col_retraso, col_interes, col_monto]:
        if col in df_cartera.columns:
            df_cartera[col] = df_cartera[col].apply(_limpiar_a_float)

    # Convertir columnas de fecha a datetime
    for col in [col_fecha_venc, col_fecha_disp]:
        if col in df_cartera.columns:
            df_cartera[col] = pd.to_datetime(
                df_cartera[col], dayfirst=True, errors="coerce"
            )

    hoy = pd.Timestamp.now().normalize()

    # -------------------------------------------------------------
    # 1. CÁLCULO DE ENCABEZADOS Y MÉTRICAS SUPERIORES
    # -------------------------------------------------------------
    # Facturas Vencidas (retraso > 0)
    df_vencidas = df_cartera[df_cartera[col_retraso] > 0].copy()
    facturas_vencidas_count = len(df_vencidas)
    mayor_atraso = (
        int(df_vencidas[col_retraso].max()) if not df_vencidas.empty else 0
    )

    # Monto Pendiente: Fecha Vencimiento > Hoy Y Estatus == "To be paid"
    condicion_monto_pendiente = (df_cartera[col_fecha_venc] > hoy) & (
        df_cartera[col_estatus].astype(str).str.strip().str.lower()
        == "to be paid"
    )
    monto_pendiente_val = df_cartera[condicion_monto_pendiente][
        col_monto
    ].sum()

    # Interés Acumulado: Suma directa de las facturas vencidas para coincidir exactamente
    interes_acumulado_val = (
        df_vencidas[col_interes].sum() if not df_vencidas.empty else 0.0
    )

    # -------------------------------------------------------------
    # ESTILOS CSS PERSONALIZADOS
    # -------------------------------------------------------------
    st.markdown(
        """
        <style>
        /* Reducción del tamaño de fuente de las métricas superiores */
        [data-testid="stMetricLabel"] {
            font-size: 13px !important;
            color: #a3a8b4 !important;
            font-weight: 500 !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 18px !important;
            font-weight: 700 !important;
            white-space: nowrap !important; /* Evita que los números se rompan en dos líneas */
        }
        
        /* Estilos de las tarjetas diarias inferiores */
        .card-diaria {
            border: 1px solid #2d2d2d;
            border-radius: 10px;
            padding: 12px 18px;
            margin-bottom: 10px;
            background-color: #161b22;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-col-left {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }
        .card-col-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }
        .top-left-title {
            font-size: 15px;
            font-weight: 700;
            color: #ffffff;
        }
        .top-right-monto {
            font-size: 15px;
            font-weight: 700;
            color: #ffffff;
        }
        .bottom-left-sub {
            font-size: 12px;
            color: #8b949e;
            margin-top: 3px;
        }
        .bottom-right-sub {
            font-size: 12px;
            color: #8b949e;
            margin-top: 3px;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Contenedor Marco Principal
    with st.container(border=True):
        st.subheader("📌 Tabla de Mora")
        st.write("") 

        # 4 Métricas de la cabecera (Muestra valores completos con formato moneda)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Facturas vencidas", f"{facturas_vencidas_count}")
        c2.metric("Monto pendiente", f"${monto_pendiente_val:,.2f}")
        c3.metric("Interés acumulado", f"${interes_acumulado_val:,.2f}")
        c4.metric("Mayor atraso", f"{mayor_atraso} días")

        st.markdown("---")

        # -------------------------------------------------------------
        # 2. SECCIÓN INFERIOR CON SCROLL: AGRUPACIÓN POR DÍA
        # -------------------------------------------------------------
        if not df_vencidas.empty:
            # Agrupar datos por la fecha que presentó atrasos
            df_vencidas["Fecha_Str"] = df_vencidas[col_fecha_venc].dt.strftime(
                "%d/%b/%Y"
            )

            df_agrupado = (
                df_vencidas.groupby("Fecha_Str")
                .agg(
                    Total_Interes=(col_interes, "sum"),
                    Facturas_Vencidas=("Fecha_Str", "count"),
                    Dias_Retraso=(col_retraso, "max"),
                    Fecha_Original=(col_fecha_venc, "max"),
                )
                .reset_index()
                .sort_values(by="Fecha_Original", ascending=False)
            )

            # Contenedor con altura fija y scroll para las filas inferiores
            with st.container(height=400, border=False):
                for _, fila in df_agrupado.iterrows():
                    dia_titulo = f"Día {fila['Fecha_Str']}"
                    monto_interes_dia = f"${fila['Total_Interes']:,.2f}"
                    facturas_num = (
                        f"Facturas vencidas: {fila['Facturas_Vencidas']}"
                    )
                    retraso_num = f"{int(fila['Dias_Retraso'])} días de retraso"

                    card_html = f"""
                    <div class="card-diaria">
                        <div class="card-col-left">
                            <div class="top-left-title">{dia_titulo}</div>
                            <div class="bottom-left-sub">{facturas_num}</div>
                        </div>
                        <div class="card-col-right">
                            <div class="top-right-monto">{monto_interes_dia}</div>
                            <div class="bottom-right-sub">{retraso_num}</div>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("No hay atrasos registrados para generar el resumen.")