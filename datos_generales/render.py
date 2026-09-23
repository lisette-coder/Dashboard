import streamlit as st

from .filtros import render_filtros_tiempo
from .kpis import render_kpis  # 👈 Mantiene tus Indicadores Clave de Rendimiento superiores
from .seccion_cartera import (
    render_barras_colocado_mensual,
    render_curva_cartera_dual,
    render_dona_composicion_capital,
    render_tarjetas_kpi,
    render_seccion_facturas_vencidas
)
from .seccion_clientes import render_curva_clientes_activos_diarios
from .seccion_dispersiones import (
    render_calendario_calor_dispersiones,
    render_curva_financiera_generica,
    render_grafica_dispersiones_por_dia_semana,
)
from .seccion_revenue import (
    render_tabla_detalle_deuda,
    render_curva_revenue_rebate_dual,
    render_curva_revenue_vs_intereses,

)

def render_datos_generales(df, df_deuda):
    # 1. ESTAS SON LAS TARJETAS KPI DE ARRIBA (Indicadores Clave de Rendimiento)
    render_kpis(df, df_deuda)

    vista = st.session_state.get("vista_activa", "dispersiones")

    col_monto = (
        "Monto Dispersado "
        if "Monto Dispersado " in df.columns
        else "Monto Dispersado"
    )

    if vista == "dispersiones":
        with st.container(border=True):
            render_curva_financiera_generica(
                df,
                columna_metrica=col_monto,
                titulo_base="Evolución de Montos",
                date_column="Fecha de Dispersión",
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col_semanal, col_calendario = st.columns([1.5, 1])

        with col_semanal:
            with st.container(border=True):
                render_grafica_dispersiones_por_dia_semana(
                    df,
                    date_column="Fecha de Dispersión",
                    monto_column=col_monto,
                )

        with col_calendario:
            with st.container(border=True):
                render_calendario_calor_dispersiones(
                    df,
                    date_column="Fecha de Dispersión",
                    monto_column=col_monto,
                )

    elif vista == "cartera":
        # Filtros de tiempo
        df_filtrado, tipo_filtro = render_filtros_tiempo(
            df, sufijo_key="cartera_vista", date_column="Fecha Vencimiento"
        )

        # 1 y 2. Distribución Layout: Gráfica Principal (Izquierda) + Tarjetas Insights (Derecha)
        col_grafica, col_insights = st.columns([4, 1.25])

        with col_grafica:
            # Evolución de Cartera Dual
            render_curva_cartera_dual(
                df=df_filtrado,
                columna_metrica="Monto Dispersado",
                titulo_base="Evolución de Cartera Dual",
                date_column="Fecha Vencimiento",
                tipo_filtro=tipo_filtro,
            )

        with col_insights:
            # Tarjetas KPI adaptadas verticalmente a un costado
            render_tarjetas_kpi(df=df, df_deuda=df_deuda, tipo_filtro=tipo_filtro)

        st.divider()

        # 3. Gráficas de Dona y Barras
        col_vencidas, col_dona, col_barras = st.columns(3)

        with col_vencidas:
            # ⚠️ Nueva tabla de Facturas Vencidas con intereses
            render_seccion_facturas_vencidas(
                df=df_filtrado,
                tasa_mensual=0.035
            )

        with col_dona:
            render_dona_composicion_capital(
                df=df_filtrado,
                df_deuda=df_deuda,
                columna_metrica="Monto Dispersado",
            )

        with col_barras:
            render_barras_colocado_mensual(
                df=df_filtrado,
                date_column="Fecha de Dispersión",
                monto_column="Monto Dispersado",
            )


    elif vista == "descuentos":
        render_curva_revenue_rebate_dual(
            df=df, 
            date_column="Fecha de Dispersión"
        )

        st.divider()

        # 2. Comparativa Mensual Revenue Kamina vs Intereses Cobrados
        render_curva_revenue_vs_intereses(
            df_consolidado=df,
            df_deuda=df_deuda,
            date_column_conv="Fecha de Dispersión",
            date_column_deuda="Mes",
        )

        st.divider()

        # 3. Tabla Detalle de Deuda
        render_tabla_detalle_deuda(df_deuda=df_deuda)
        

    elif vista == "clientes":
        render_curva_clientes_activos_diarios(df)

    elif vista == "intereses":
        render_curva_revenue_vs_intereses(
            df_consolidado=df, df_deuda=df_deuda
        )