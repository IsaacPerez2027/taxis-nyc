"""Parte 2: tipos de zona (K-Means + PCA), con filtros y selección de puntos."""
import pandas as pd
import plotly.express as px
import streamlit as st

from utils import COLORES_GRUPO, COLORES_HEX, cargar_metricas, cargar_zonas

st.title(":material/hub: Tipos de zona")
st.write("**Qué tipo de zona es:** no se planifica igual un aeropuerto que una zona de bares. "
         "Cada punto es una zona; las que se parecen en cómo se usan quedan cerca y del mismo color.")

zonas = cargar_zonas()
metricas = cargar_metricas()
grupos = sorted(zonas["grupo_nombre"].unique())

elegidos = st.pills("Grupos", grupos, selection_mode="multi", default=grupos)
visibles = zonas[zonas["grupo_nombre"].isin(elegidos)]
if visibles.empty:
    st.warning("Elija al menos un grupo para ver las zonas.")
    st.stop()

varianza = sum(metricas["pca_varianza"])
columna_grafico, columna_detalle = st.columns([3, 2])

with columna_grafico:
    figura = px.scatter(visibles, x="pca1", y="pca2", color="grupo_nombre", custom_data=["zona_id"], hover_name="nombre", color_discrete_map=COLORES_HEX,
                        hover_data={"distrito": True, "viajes_dia": ":.0f", "pca1": False, "pca2": False, "grupo_nombre": False},
                        labels={"pca1": f"Componente 1 ({metricas['pca_varianza'][0]:.0%})",
                                "pca2": f"Componente 2 ({metricas['pca_varianza'][1]:.0%})", "grupo_nombre": "Grupo"})
    figura.update_traces(marker=dict(size=11, line=dict(width=1, color="white")))
    figura.update_layout(title=f"Las {len(visibles)} zonas en dos dimensiones (PCA conserva {varianza:.0%} de la variación)",
                         legend=dict(orientation="h", y=-0.25), margin=dict(t=50))
    evento = st.plotly_chart(figura, on_select="rerun", selection_mode=("points", "box", "lasso"), key="mapa_pca",
                             width="stretch")
    st.caption("Seleccione puntos (clic, caja o lazo) para ver su detalle a la derecha y en la tabla.")

seleccionadas = [p["customdata"][0] for p in evento.selection.points]
detalle = visibles[visibles["zona_id"].isin(seleccionadas)] if seleccionadas else visibles.iloc[0:0]

with columna_detalle:
    if detalle.empty:
        st.subheader("Qué distingue a cada grupo")
        for grupo in metricas["grupos"]:
            if grupo["nombre"] in elegidos:
                with st.container(border=True):
                    st.badge(grupo["nombre"], color=COLORES_GRUPO.get(grupo["nombre"], "gray"))
                    st.write(grupo["descripcion"])
                    st.caption(f"{int(grupo['zonas'])} zonas · {grupo['viajes_dia']:,.0f} viajes por día (mediana) · "
                               f"{grupo['dist_mediana']:.1f} millas · tarifa ${grupo['tarifa_mediana']:.0f}")
    else:
        st.subheader(f"{len(detalle)} zona(s) seleccionada(s)")
        for fila in detalle.head(6).itertuples():
            with st.container(border=True):
                st.markdown(f"**{fila.nombre}** · {fila.distrito}")
                st.badge(fila.grupo_nombre, color=COLORES_GRUPO.get(fila.grupo_nombre, "gray"))
                a, b, c = st.columns(3)
                a.metric("Viajes por día", f"{fila.viajes_dia:,.0f}")
                b.metric("Distancia", f"{fila.dist_mediana:.1f} mi")
                c.metric("Tarifa", f"${fila.tarifa_mediana:.0f}")
        if len(detalle) > 6:
            st.caption(f"…y {len(detalle) - 6} más en la tabla.")
        if len(detalle) == 1 and bool(detalle.iloc[0]["se_pronostica"]):
            if st.button("Ver el pronóstico de esta zona", icon=":material/insights:"):
                st.session_state["zona_id"] = int(detalle.iloc[0]["zona_id"])
                st.query_params["zona"] = str(int(detalle.iloc[0]["zona_id"]))
                st.switch_page("paginas/pronostico.py")
        elif len(detalle) == 1:
            st.caption("Esta zona tiene menos de 3,000 viajes en el mes: se segmenta, pero no se pronostica.")

tabla = (detalle if not detalle.empty else visibles).copy()
tabla["pct_noche"] = tabla["pct_22_5"] * 100
tabla["pct_finde"] = tabla["pct_finde"] * 100
st.subheader("Tabla de zonas" + (" seleccionadas" if not detalle.empty else ""))
st.dataframe(
    tabla[["nombre", "distrito", "grupo_nombre", "viajes_dia", "dist_mediana", "tarifa_mediana", "propina_mediana",
           "pct_noche", "pct_finde", "perfil_24h", "se_pronostica"]],
    hide_index=True, width="stretch",
    column_config={
        "nombre": "Zona", "distrito": "Distrito", "grupo_nombre": "Grupo",
        "viajes_dia": st.column_config.ProgressColumn("Viajes por día", min_value=0, max_value=float(zonas["viajes_dia"].max()), format="%.0f"),
        "dist_mediana": st.column_config.NumberColumn("Distancia (mi)", format="%.1f"),
        "tarifa_mediana": st.column_config.NumberColumn("Tarifa ($)", format="$%.0f"),
        "propina_mediana": st.column_config.NumberColumn("Propina ($)", format="$%.2f"),
        "pct_noche": st.column_config.NumberColumn("De noche (22-5 h)", format="%.0f%%"),
        "pct_finde": st.column_config.NumberColumn("Fin de semana", format="%.0f%%"),
        "perfil_24h": st.column_config.LineChartColumn("Viajes a lo largo del día", y_min=0),
        "se_pronostica": st.column_config.CheckboxColumn("Tiene pronóstico"),
    },
)

with st.expander("¿Por qué 4 grupos? Coeficiente de silueta"):
    siluetas = pd.DataFrame({"k": [int(k) for k in metricas["siluetas"]], "silueta": list(metricas["siluetas"].values())})
    grafico = px.line(siluetas, x="k", y="silueta", markers=True, title="Coeficiente de silueta para k = 2 a 7")
    grafico.add_vline(x=metricas["k_elegido"], line_dash="dash", line_color="red")
    st.plotly_chart(grafico, width="stretch")
    st.write(f"La silueta mide qué tan separados están los grupos (más alto es mejor). La mayor es la de **k = {metricas['k_elegido']}**. "
             f"Los dos ejes del mapa conservan el **{varianza:.0%}** de la variación original (componente 1: "
             f"{metricas['pca_varianza'][0]:.0%}, componente 2: {metricas['pca_varianza'][1]:.0%}).")
