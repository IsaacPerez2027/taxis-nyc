"""Funciones compartidas por todas las páginas: conexión con la API, selectores y datos precalculados."""
import json
import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st

DATOS = Path(__file__).parent / "data"
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
COLORES_GRUPO = {
    "Aeropuertos y viajes largos": "red",
    "Centro de alta demanda": "blue",
    "Vida nocturna y fin de semana": "violet",
    "Barrios residenciales de baja demanda": "green",
}
COLORES_HEX = {"Aeropuertos y viajes largos": "#D62728", "Centro de alta demanda": "#1F77B4",
               "Vida nocturna y fin de semana": "#8E44AD", "Barrios residenciales de baja demanda": "#2CA02C"}
ZONA_INICIAL = 161  # Midtown Center, la zona con más viajes


# ---------- Conexión con la API ----------
def url_api() -> str:
    """La dirección de la API vive en st.secrets (no en el código); en local se usa la variable API_URL."""
    try:
        return st.secrets["API_URL"].rstrip("/")
    except Exception:
        return os.environ.get("API_URL", "http://localhost:8000").rstrip("/")


@st.cache_data(ttl=3600, show_spinner=False)
def _pedir(url: str, ruta: str, parametros: tuple):
    """Una sola llamada a la API por consulta cada hora (si falla, no se guarda en caché)."""
    respuesta = requests.get(url + ruta, params=dict(parametros), timeout=90)  # 90 s: Render tarda ~1 min en despertar
    respuesta.raise_for_status()
    return respuesta.json()


def consultar(ruta: str, **parametros):
    """Pide datos a la API mostrando el avance; si falla explica qué pasó en lugar de mostrar un error de Python."""
    with st.status("Conectando con la API…", expanded=False) as estado:
        try:
            datos = _pedir(url_api(), ruta, tuple(sorted(parametros.items())))
        except requests.HTTPError as error:
            estado.update(label="La API respondió con un aviso", state="error")
            if error.response is not None and error.response.status_code == 404:
                st.warning("No hay datos para esa zona o fecha. Elija otra combinación.")
            else:
                st.error("La API respondió con un error. Intente de nuevo en un momento.")
            st.stop()
        except requests.RequestException:
            estado.update(label="No se pudo conectar con la API", state="error")
            st.error(
                "No se pudo conectar con la API. En el plan gratuito de Render la API se duerme tras 15 minutos "
                "sin uso y tarda cerca de un minuto en despertar: espere un momento y recargue la página."
            )
            st.stop()
        estado.update(label="Conectado con la API", state="complete")
    return datos


@st.cache_data(ttl=60, show_spinner=False)
def api_en_linea() -> bool:
    try:
        return requests.get(url_api() + "/", timeout=5).ok
    except requests.RequestException:
        return False


# ---------- Datos precalculados en el cuaderno ----------
@st.cache_data
def cargar_metricas() -> dict:
    return json.loads((DATOS / "metricas.json").read_text(encoding="utf-8"))


@st.cache_data
def cargar_zonas() -> pd.DataFrame:
    zonas = pd.read_csv(DATOS / "zonas_segmentadas.csv")
    zonas["perfil_24h"] = zonas["perfil_24h"].map(lambda t: [float(v) for v in t.split(";")])
    return zonas


@st.cache_data
def cargar_error_diario_zona() -> pd.DataFrame:
    return pd.read_csv(DATOS / "error_diario_zona.csv")


# ---------- Fechas y selectores ----------
def etiqueta_fecha(iso: str, futuro: str | None = None) -> str:
    f = date.fromisoformat(iso)
    texto = f"{DIAS[f.weekday()]} {f.day} {MESES[f.month - 1]}"
    return f"{texto} · mañana" if iso == futuro else texto


def _recordar(clave_estado: str, clave_widget: str, parametro: str):
    st.session_state[clave_estado] = st.session_state[clave_widget]
    st.query_params[parametro] = str(st.session_state[clave_widget])


def selector_zona_fecha(info: dict, pagina: str, mostrar_fecha: bool = True):
    """Selectores de zona y fecha que recuerdan la elección al cambiar de página y en el link (query_params)."""
    zonas = {z["id"]: f'{z["nombre"]} ({z["distrito"]})' for z in info["zonas"]}
    fechas = info["fechas"]
    futuro = info["fecha_sin_datos_reales"]

    try:
        zona_guardada = st.session_state.get("zona_id") or int(st.query_params.get("zona", ZONA_INICIAL))
    except ValueError:  # un link con una zona que no es un número
        zona_guardada = ZONA_INICIAL
    zona_guardada = zona_guardada if zona_guardada in zonas else ZONA_INICIAL
    fecha_guardada = st.session_state.get("fecha") or st.query_params.get("fecha", fechas[0])
    fecha_guardada = fecha_guardada if fecha_guardada in fechas else fechas[0]
    st.session_state["zona_id"], st.session_state["fecha"] = zona_guardada, fecha_guardada

    zona_id = st.selectbox("Zona", list(zonas), index=list(zonas).index(zona_guardada), format_func=zonas.get,
                           key=f"zona_{pagina}", on_change=_recordar, args=("zona_id", f"zona_{pagina}", "zona"))
    fecha = fecha_guardada
    if mostrar_fecha:
        elegida = st.segmented_control("Fecha", fechas, default=fecha_guardada, key=f"fecha_{pagina}",
                                       format_func=lambda f: etiqueta_fecha(f, futuro),
                                       on_change=_recordar, args=("fecha", f"fecha_{pagina}", "fecha"))
        fecha = elegida or fecha_guardada
    return int(zona_id), fecha, zonas[int(zona_id)]


# ---------- Cálculos ----------
def cuantil_optimo(costo_perdido: float, costo_ocioso: float) -> float:
    return costo_perdido / (costo_perdido + costo_ocioso)


def taxis_a_enviar(horas: list[dict], nivel: float, cuantiles: list[float]) -> np.ndarray:
    """Interpola el cuantil `nivel` entre p10 y p90 y redondea hacia arriba (un taxi atiende un viaje por hora)."""
    nivel = float(np.clip(nivel, cuantiles[0], cuantiles[-1]))
    claves = [f"p{int(round(q * 100))}" for q in cuantiles]
    return np.array([np.ceil(np.interp(nivel, cuantiles, [h["cuantiles"][c] for c in claves])) for h in horas])


def costo_total(enviados, real, costo_ocioso: float, costo_perdido: float) -> float:
    enviados, real = np.asarray(enviados, dtype=float), np.asarray(real, dtype=float)
    return float((np.maximum(enviados - real, 0) * costo_ocioso + np.maximum(real - enviados, 0) * costo_perdido).sum())
