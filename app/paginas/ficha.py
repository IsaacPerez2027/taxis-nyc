"""Parte 4: ficha del modelo y comunicación ética. Todas las cifras salen del cuaderno (metricas.json)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from utils import cargar_metricas

metricas = cargar_metricas()
prueba = metricas["prueba"]

st.title(":material/description: Ficha del modelo")
st.write("**Cuánto confiar:** qué hace el modelo, qué tan bien lo hace, dónde falla y para qué no debe usarse.")

with st.popover("Glosario", icon=":material/menu_book:"):
    st.markdown(
        """
- **Cuantil / rango del 80 %:** el rango entre el cuantil 10 % y el 90 %: se espera que 8 de cada 10 horas caigan dentro.
- **WAPE:** «¿qué porcentaje de los viajes me equivoco?»: suma de los errores / suma de los viajes reales.
- **Cobertura:** cuántas horas reales cayeron de verdad dentro del rango.
- **Regla simple:** «igual que hace una semana», lo mínimo que un modelo debe superar.
"""
    )

pestana_ficha, pestana_graficos = st.tabs(["Ficha", "Gráficos"])
with pestana_ficha:
    st.markdown(metricas["ficha_md"].split("\n", 1)[1])   # sin la primera línea: es el título que ya tiene la página

with pestana_graficos:
    a, b, c = st.columns(3)
    a.metric("Error del modelo", f"{prueba['wape_modelo']:.1%}", border=True,
             delta=f"{(prueba['wape_modelo'] - prueba['wape_semana']) * 100:+.1f} pts frente a «hace una semana»", delta_color="inverse")
    b.metric("Error de «hace una semana»", f"{prueba['wape_semana']:.1%}", border=True)
    c.metric("El rango del 80 % cubre", f"{prueba['cobertura_80']:.1%}", border=True, delta="meta: 80 %", delta_color="off")

    por_tipo = pd.DataFrame(metricas["por_tipo_de_zona"])
    larga = por_tipo.melt(id_vars=["grupo_nombre", "zonas"], value_vars=["wape_modelo", "wape_semana"], var_name="regla", value_name="error")
    larga["regla"] = larga["regla"].map({"wape_modelo": "Modelo", "wape_semana": "Igual que hace una semana"})
    larga["error"] = larga["error"] * 100
    grafico = px.bar(larga, x="grupo_nombre", y="error", color="regla", barmode="group", color_discrete_sequence=["#F5A800", "#6B7280"],
                     labels={"grupo_nombre": "Tipo de zona", "error": "Error (WAPE, %)", "regla": ""},
                     title="¿Dónde se equivoca más? Error por tipo de zona")
    st.plotly_chart(grafico, width="stretch")
    st.caption("Zonas pronosticadas por tipo: " + " · ".join(f"{f['grupo_nombre']}: {int(f['zonas'])}" for f in metricas["por_tipo_de_zona"]))

    cobertura = pd.DataFrame({"nivel": [int(k[1:]) for k in prueba["cobertura_por_cuantil"]],
                              "observado": [v * 100 for v in prueba["cobertura_por_cuantil"].values()]})
    calibracion = px.line(cobertura, x="nivel", y="observado", markers=True, title="Calibración: ¿cada cuantil cubre lo que promete?",
                          labels={"nivel": "Cuantil (%)", "observado": "% de horas reales por debajo"})
    calibracion.add_shape(type="line", x0=10, y0=10, x1=90, y1=90, line=dict(dash="dash", color="gray"))
    st.plotly_chart(calibracion, width="stretch")

    importancia = pd.Series(metricas["importancia_variables"]).sort_values().rename("importancia").rename_axis("variable").reset_index()
    st.plotly_chart(px.bar(importancia, x="importancia", y="variable", orientation="h", title="Qué variables usa el modelo",
                           color_discrete_sequence=["#F5A800"]), width="stretch")

st.divider()
st.subheader("¿Le fue útil esta herramienta?")
st.feedback("stars", key="estrellas",
            on_change=lambda: st.toast(f"¡Gracias por su opinión! ({st.session_state['estrellas'] + 1} de 5 estrellas)", icon=":material/star:"))
