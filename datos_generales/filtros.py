import streamlit as st
import pandas as pd

from .constantes import NOMBRES_MESES


def render_filtros_tiempo(df, sufijo_key, date_column="Fecha de Dispersión"):
    """Renderiza controles interactivos de filtrado por Año, Rango de Meses o Mes Específico."""
    if date_column not in df.columns:
        st.warning(
            f"No se encontró la columna de fecha '{date_column}' en los datos."
        )
        return df.copy(), "Sin Filtro"

    df_copia = df.copy()
    df_copia[date_column] = pd.to_datetime(df_copia[date_column], errors="coerce")
    df_copia["_Anio_Filtro"] = df_copia[date_column].dt.year
    df_copia["_Mes_Filtro"] = df_copia[date_column].dt.month

    anos_disponibles = sorted(df_copia["_Anio_Filtro"].dropna().unique())
    if not anos_disponibles:
        return df_copia, "Sin Filtro"

    col_f1, col_f2 = st.columns([1, 2])

    with col_f1:
        tipo_filtro = st.radio(
            "Filtrar por:",
            ["Año Completo", "Rango de Meses", "Mes Específico"],
            index=0,
            key=f"radio_tiempo_{sufijo_key}",
        )

    with col_f2:
        if tipo_filtro == "Mes Específico":
            anio_sel = st.selectbox(
                "Selecciona el Año",
                anos_disponibles,
                key=f"anio_mes_{sufijo_key}",
            )
            meses_disponibles = sorted(
                df_copia[df_copia["_Anio_Filtro"] == anio_sel][
                    "_Mes_Filtro"
                ].dropna().unique()
            )
            mes_sel = st.selectbox(
                "Selecciona el Mes",
                meses_disponibles,
                format_func=lambda x: NOMBRES_MESES.get(x, x),
                key=f"mes_esp_{sufijo_key}",
            )
            df_filtrado = df_copia[
                (df_copia["_Anio_Filtro"] == anio_sel)
                & (df_copia["_Mes_Filtro"] == mes_sel)
            ].copy()

        elif tipo_filtro == "Rango de Meses":
            anio_sel = st.selectbox(
                "Selecciona el Año para el Rango",
                anos_disponibles,
                key=f"anio_rango_{sufijo_key}",
            )
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mes_inicio = st.selectbox(
                    "Mes Inicial",
                    list(NOMBRES_MESES.keys()),
                    format_func=lambda x: NOMBRES_MESES[x],
                    index=0,
                    key=f"mes_ini_{sufijo_key}",
                )
            with col_m2:
                mes_fin = st.selectbox(
                    "Mes Final",
                    list(NOMBRES_MESES.keys()),
                    format_func=lambda x: NOMBRES_MESES[x],
                    index=len(NOMBRES_MESES) - 1,
                    key=f"mes_fin_{sufijo_key}",
                )
            df_filtrado = df_copia[
                (df_copia["_Anio_Filtro"] == anio_sel)
                & (df_copia["_Mes_Filtro"] >= mes_inicio)
                & (df_copia["_Mes_Filtro"] <= mes_fin)
            ].copy()

        else:
            anio_sel = st.selectbox(
                "Selecciona el Año Completo",
                anos_disponibles,
                key=f"anio_comp_{sufijo_key}",
            )
            df_filtrado = df_copia[df_copia["_Anio_Filtro"] == anio_sel].copy()

    df_filtrado = df_filtrado.drop(columns=["_Anio_Filtro", "_Mes_Filtro"])
    return df_filtrado, tipo_filtro