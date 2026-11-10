"""Taxis NYC: una app para quien toma decisiones. Punto de entrada: define las páginas y la barra lateral."""
import streamlit as st

from utils import api_en_linea, url_api

st.set_page_config(page_title="Taxis NYC", page_icon=":material/local_taxi:", layout="wide")

paginas = st.navigation(
    {
        "Planear": [
            st.Page("paginas/pronostico.py", title="Pronóstico", icon=":material/insights:", default=True),
            st.Page("paginas/decision.py", title="Cuántos taxis enviar", icon=":material/local_taxi:"),
        ],
        "Entender": [
            st.Page("paginas/segmentacion.py", title="Tipos de zona", icon=":material/hub:"),
            st.Page("paginas/ficha.py", title="Ficha del modelo", icon=":material/description:"),
        ],
        "Vigilar": [
            st.Page("paginas/monitoreo.py", title="Monitoreo del error", icon=":material/monitoring:"),
        ],
    }
)

with st.sidebar:
    st.title(":material/local_taxi: Taxis NYC")
    st.caption("Qué esperar, qué tipo de zona es, cuántos taxis enviar y cuánto confiar.")
    if api_en_linea():
        st.badge("API en línea", icon=":material/check_circle:", color="green")
    else:
        st.badge("API durmiendo o sin conexión", icon=":material/hourglass_top:", color="orange")
        st.caption("En Render gratis la API tarda cerca de un minuto en despertar.")
    st.divider()
    st.caption(f"API: {url_api()}")

paginas.run()
