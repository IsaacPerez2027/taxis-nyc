"""Parte 3: cuántos taxis enviar según el costo de equivocarse."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import consultar, costo_total, cuantil_optimo, selector_zona_fecha, taxis_a_enviar

st.title(":material/local_taxi: Cuántos taxis enviar")
st.write("**Qué hacer:** según lo que le cuesta equivocarse hacia arriba o hacia abajo, la app calcula cuántos taxis enviar cada hora.")

info = consultar("/info")
zona_id, fecha, nombre_zona = selector_zona_fecha(info, "decision")
datos = consultar("/pronostico", zona_id=zona_id, fecha=fecha)


@st.fragment
def panel_decision(horas, cuantiles, nombre_zona, zona_id, fecha):
    """Los controles y los resultados viven juntos: mover un control no recarga toda la página."""
    columna_a, columna_b = st.columns(2)
    costo_ocioso = columna_a.number_input("Un taxi una hora sin pasajero cuesta (USD)", min_value=1.0, value=10.0, step=1.0)
    costo_perdido = columna_b.number_input("Un pasajero que no encuentra taxi cuesta (USD)", min_value=1.0, value=40.0, step=1.0)

    nivel = cuantil_optimo(costo_perdido, costo_ocioso)
    st.latex(r"\text{cuantil óptimo} = \frac{C_p}{C_p + C_o} = \frac{%g}{%g + %g} = %.2f" % (costo_perdido, costo_perdido, costo_ocioso, nivel))
    recortado = nivel < cuantiles[0] or nivel > cuantiles[-1]
    if nivel > 0.5:
        explicacion = (f"Perder un pasajero cuesta **{costo_perdido / costo_ocioso:.1f} veces** más que un taxi parado, así que conviene "
                       f"**enviar más que el pronóstico central**: se cubre el {nivel:.0%} de los casos probables.")
    elif nivel < 0.5:
        explicacion = (f"Un taxi parado cuesta **más** que perder un pasajero, así que conviene **enviar menos que el pronóstico central**: "
                       f"se cubre solo el {nivel:.0%} de los casos probables.")
    else:
        explicacion = "Los dos errores cuestan lo mismo: se envía exactamente el pronóstico central."
    st.info(explicacion, icon=":material/lightbulb:")
    if recortado:
        st.caption("El modelo entrega cuantiles de 10 % a 90 %: con estos costos se usa el extremo más cercano.")

    recomendados = taxis_a_enviar(horas, nivel, cuantiles)
    centrales = np.array([np.ceil(h["cuantiles"]["p50"]) for h in horas])
    semana = np.array([h["hace_una_semana"] for h in horas], dtype=float)
    reales = [h["real"] for h in horas]
    hay_reales = all(r is not None for r in reales)
    x = [h["hora"] for h in horas]

    figura = go.Figure()
    figura.add_trace(go.Bar(x=x, y=recomendados, name="Taxis recomendados", marker_color="#F5A800"))
    figura.add_trace(go.Scatter(x=x, y=centrales, mode="lines", name="Pronóstico central (p50)", line=dict(color="#6B7280", dash="dot")))
    if hay_reales:
        figura.add_trace(go.Scatter(x=x, y=reales, mode="markers", name="Viajes reales", marker=dict(color="black", size=7)))
    figura.update_layout(title=f"{nombre_zona}: taxis a enviar por hora", xaxis_title="Hora del día", yaxis_title="Taxis",
                         legend=dict(orientation="h", y=-0.25), margin=dict(t=50))
    figura.update_xaxes(dtick=2)
    st.plotly_chart(figura, width="stretch")

    if hay_reales:
        reales_np = np.array(reales, dtype=float)
        costo_recomendado = costo_total(recomendados, reales_np, costo_ocioso, costo_perdido)
        costo_central = costo_total(centrales, reales_np, costo_ocioso, costo_perdido)
        costo_semana = costo_total(semana, reales_np, costo_ocioso, costo_perdido)
        st.subheader("¿Cuánto habría costado cada decisión ese día?")
        a, b, c = st.columns(3)
        a.metric("Nuestra recomendación", f"${costo_recomendado:,.0f}", border=True,
                 delta=f"{costo_recomendado - costo_central:+,.0f} frente al pronóstico central", delta_color="inverse")
        b.metric("Enviar el pronóstico central (p50)", f"${costo_central:,.0f}", border=True,
                 delta=f"{costo_central - costo_recomendado:+,.0f} frente a la recomendación", delta_color="inverse")
        c.metric("Igual que hace una semana", f"${costo_semana:,.0f}", border=True,
                 delta=f"{costo_semana - costo_recomendado:+,.0f} frente a la recomendación", delta_color="inverse")
        st.caption("Costo = taxis ociosos × costo de un taxi parado + pasajeros perdidos × costo de un pasajero perdido, hora por hora. "
                   "Un costo que sube es malo.")
    else:
        st.info("El 1 de febrero es «mañana»: no hay viajes reales para comparar costos, pero el plan ya se puede descargar.",
                icon=":material/event_upcoming:")

    plan = pd.DataFrame({"hora": x, "taxis_recomendados": recomendados.astype(int), "pronostico_central_p50": centrales.astype(int),
                         "minimo_probable_p10": [h["cuantiles"]["p10"] for h in horas], "maximo_probable_p90": [h["cuantiles"]["p90"] for h in horas]})
    st.download_button("Descargar el plan de taxis por hora (CSV)", plan.to_csv(index=False).encode("utf-8"),
                       file_name=f"plan_taxis_{zona_id}_{fecha}.csv", mime="text/csv", icon=":material/download:")


panel_decision(datos["horas"], info["cuantiles"], nombre_zona, zona_id, fecha)
