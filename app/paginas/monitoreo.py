"""Extra (+10): monitoreo del error día a día de la semana de prueba, con alerta."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import cargar_error_diario_zona, cargar_metricas, cargar_zonas, etiqueta_fecha

metricas = cargar_metricas()
st.title(":material/monitoring: Monitoreo del error")
st.write("Mide cuánto se equivocó el pronóstico **cada día** de la semana de prueba y avisa cuando el error pasa un límite.")

limite_sugerido = metricas["limite_wape"] * 100
limite = st.slider("Límite de alerta (error diario, %)", 5.0, 50.0, round(limite_sugerido, 1), 0.5,
                   help="Por defecto: 1.25 veces el error diario promedio de la semana de validación.")

diario = pd.DataFrame(metricas["error_diario"])
diario["fecha_texto"] = diario["fecha"].map(etiqueta_fecha)
diario["modelo"] = diario["wape_modelo"] * 100
diario["semana"] = diario["wape_semana"] * 100
sobre_limite = diario[diario["modelo"] > limite]

a, b, c = st.columns(3)
a.metric("Error del último día", f"{diario['modelo'].iloc[-1]:.1f}%", border=True, chart_data=diario["modelo"].tolist(), chart_type="line")
b.metric("Error promedio de la semana", f"{diario['modelo'].mean():.1f}%", border=True)
c.metric("Días sobre el límite", f"{len(sobre_limite)} de {len(diario)}", border=True)

if sobre_limite.empty:
    st.success(f"Sin alertas: ningún día pasó el límite de {limite:.1f}%. El peor día fue "
               f"{diario.loc[diario['modelo'].idxmax(), 'fecha_texto']} ({diario['modelo'].max():.1f}%).", icon=":material/check_circle:")
else:
    st.error("**Alerta:** el error pasó el límite el " + ", ".join(sobre_limite["fecha_texto"]) +
             ". Conviene revisar qué cambió (feriado, clima, un evento) y volver a entrenar.", icon=":material/warning:")

figura = go.Figure()
figura.add_trace(go.Scatter(x=diario["fecha_texto"], y=diario["modelo"], mode="lines+markers", name="Modelo", line=dict(color="#C77F00", width=3)))
figura.add_trace(go.Scatter(x=diario["fecha_texto"], y=diario["semana"], mode="lines+markers", name="Igual que hace una semana",
                            line=dict(color="#6B7280", dash="dot")))
figura.add_hline(y=limite, line_dash="dash", line_color="red", annotation_text="Límite de alerta", annotation_position="top left")
figura.update_layout(title="Error diario (WAPE) en la semana de prueba", yaxis_title="Error (%)", xaxis_title="", legend=dict(orientation="h", y=-0.2))
st.plotly_chart(figura, width="stretch")

with st.expander("Ver el error de una zona en particular"):
    zonas = cargar_zonas().set_index("zona_id")["nombre"]
    por_zona = cargar_error_diario_zona()
    zona = st.selectbox("Zona", sorted(por_zona["PULocationID"].unique()), format_func=lambda z: zonas.get(z, str(z)))
    detalle = por_zona[por_zona["PULocationID"] == zona].assign(fecha_texto=lambda d: d["fecha"].map(etiqueta_fecha), error=lambda d: d["wape_modelo"] * 100)
    st.bar_chart(detalle, x="fecha_texto", y="error", y_label="Error (WAPE, %)", x_label="")
    st.caption("El límite se definió para el total de la ciudad. En zonas pequeñas el error diario es más alto porque con pocos viajes el azar pesa más.")
