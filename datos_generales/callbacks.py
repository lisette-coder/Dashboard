import streamlit as st

def cambiar_vista(nueva_vista):
    st.session_state.vista_activa = nueva_vista
