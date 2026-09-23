import streamlit as st

st.set_page_config(
    page_title="Kamina Dashboard",
    page_icon="📊",
    layout="wide"
)


st.title("Kamina Dashboard")

st.markdown(
    """
    <div style="background-color: #0E1117; padding: 22px; border-radius: 12px; margin-bottom: 25px; border-left: 6px solid #0047AB;">
        <h1 style="color: white; margin:0; padding:0; font-size: 2.2rem;">🏢 Portal Operativo y Financiero</h1>
        <p style="color: #A0AAB2; margin-top: 6px; font-size: 1.05rem;">Kamina Credit &bull; Sistema Integral de Análisis y Control</p>
    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown("Bienvenid@ al sistema integral de análisis. Utiliza el **menú lateral izquierdo** para navegar entre los módulos especializados:")

st.write("") # Espacio visual

# Grilla de 2 columnas x 2 filas para las tarjetas de módulos
col_a, col_b = st.columns(2)

# MÓDULOS ACTIVOS
with col_a:
    with st.container(border=True):
        st.subheader("📊 Datos Generales")
        st.caption("Visualización global de KPIs clave, filtros avanzados y gráficas dinámicas.")
        st.markdown("""
        **Incluye 5 secciones clave:**
        * 🚀 **Dispersiones**
        * 👥 **Cartera de Clientes**
        * 💰 **Ingresos**
        * 📋 **Resumen de Clientes**
        * 🏦 **Capital**
        """)

with col_b:
    with st.container(border=True):
        st.subheader("💸 Clientes")
        st.caption("Estrategia y análisis de segmentación de la cartera.")
        st.markdown("""
        **Funcionalidades principales:**
        * 🎯 Identificación de clientes prioritarios.
        * 📊 Segmentación por **ticket promedio**.
        * 🔄 Análisis por **frecuencia de disposición**.
        """)

st.write("") # Espacio visual

# MÓDULOS EN PREPARACIÓN
col_c, col_d = st.columns(2)

with col_c:
    with st.container(border=True):
        st.subheader("🔮 Análisis Predictivos")
        st.caption("Modelos avanzados de proyección de comportamientos y tendencias.")
        st.warning("⚠️ **Módulo en preparación...**")

with col_d:
    with st.container(border=True):
        st.subheader("🛡️ Riesgos")
        st.caption("Evaluación de salud crediticia, mora y mitigación de pérdidas.")
        st.warning("⚠️ **Módulo en preparación...**")

st.divider()


#  # Pie de página y cierre de sesión
# col_user, col_logout = st.columns([3, 1])
# with col_logout:
#     if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
#         st.session_state.autenticado = False
#         st.rerun()

