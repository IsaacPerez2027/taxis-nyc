"""Parte 1: pronóstico de viajes por hora con su rango de incertidumbre."""
import plotly.graph_objects as go
import streamlit as st

from utils import consultar, selector_zona_fecha

st.title(":material/insights: Pronóstico de viajes por hora")
st.write("**Qué esperar:** cuántos viajes de taxi habrá cada hora en una zona, con el rango en el que casi seguro caerá.")


@st.dialog("¿Cómo leer este gráfico?")
def ayuda():
    st.markdown(
        """
- La **línea** es el pronóstico central: la cantidad de viajes que el modelo cree más probable.
- La **banda amarilla** es el rango del 80 %: en 8 de cada 10 horas, los viajes reales caen dentro de ella.
- Los **puntos negros** son los viajes que realmente hubo (solo existen para los días ya ocurridos).
- La **línea punteada** es una regla simple: «igual que hace una semana».
- Una banda **ancha** significa más incertidumbre: en esa hora conviene ser prudente.
"""
    )


info = consultar("/info")
columna_controles, columna_ayuda = st.columns([5, 1], vertical_alignment="bottom")
with columna_controles:
    zona_id, fecha, nombre_zona = selector_zona_fecha(info, "pronostico")
with columna_ayuda:
    if st.button("Ayuda", icon=":material/help:", width="stretch"):
        ayuda()

datos = consultar("/pronostico", zona_id=zona_id, fecha=fecha)
horas = datos["horas"]
x = [h["hora"] for h in horas]
p10, p50, p90 = ([h["cuantiles"][k] for h in horas] for k in ("p10", "p50", "p90"))
semana = [h["hace_una_semana"] for h in horas]
reales = [h["real"] for h in horas]
hay_reales = all(r is not None for r in reales)

hora_pico = x[max(range(24), key=lambda i: p50[i])]
columnas = st.columns(4)
columnas[0].metric("Viajes esperados en el día", f"{sum(p50):,.0f}", border=True, chart_data=p50, chart_type="area")
columnas[1].metric("Rango del 80 % del día", f"{sum(p10):,.0f} a {sum(p90):,.0f}", border=True, chart_data=p90, chart_type="line")
columnas[2].metric("Hora con más viajes", f"{hora_pico}:00", border=True)
if hay_reales:
    error_modelo = sum(abs(r - p) for r, p in zip(reales, p50)) / max(sum(reales), 1)
    error_semana = sum(abs(r - s) for r, s in zip(reales, semana)) / max(sum(reales), 1)
    columnas[3].metric("Error del pronóstico en el día", f"{error_modelo:.1%}", border=True,
                       delta=f"{(error_modelo - error_semana) * 100:+.1f} pts frente a «hace una semana»", delta_color="inverse")
else:
    columnas[3].metric("Viajes reales", "aún no hay", border=True)

figura = go.Figure()
figura.add_trace(go.Scatter(x=x, y=p90, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
figura.add_trace(go.Scatter(x=x, y=p10, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(245,168,0,0.28)",
                            name="Rango del 80 % (p10 a p90)"))
figura.add_trace(go.Scatter(x=x, y=p50, mode="lines", line=dict(color="#C77F00", width=3), name="Pronóstico central (p50)"))
figura.add_trace(go.Scatter(x=x, y=semana, mode="lines", line=dict(color="#6B7280", width=1.5, dash="dot"), name="Igual que hace una semana"))
if hay_reales:
    figura.add_trace(go.Scatter(x=x, y=reales, mode="markers", marker=dict(color="black", size=8), name="Viajes reales"))
figura.update_layout(title=f"{nombre_zona}: viajes por hora", xaxis_title="Hora del día", yaxis_title="Viajes por hora",
                     hovermode="x unified", legend=dict(orientation="h", y=-0.2), margin=dict(t=50))
figura.update_xaxes(dtick=2)
st.plotly_chart(figura, width="stretch")

if not hay_reales:
    st.info("El **1 de febrero es «mañana»**: todavía no hay viajes reales, solo el pronóstico. "
            "Así se vería una decisión tomada hoy para mañana.", icon=":material/event_upcoming:")

with st.expander("Ver la tabla hora por hora"):
    import pandas as pd
    tabla = pd.DataFrame({"Hora": x, "Pronóstico (p50)": p50, "Mínimo probable (p10)": p10, "Máximo probable (p90)": p90,
                          "Hace una semana": semana, "Real": reales})
    st.dataframe(tabla, hide_index=True, width="stretch",
                 column_config={"Pronóstico (p50)": st.column_config.ProgressColumn("Pronóstico (p50)", min_value=0,
                                                                                    max_value=float(max(p90)), format="%.0f")})
