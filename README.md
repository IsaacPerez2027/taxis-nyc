# Taxis NYC: una app para quien toma decisiones

Pronóstico de viajes de taxi amarillo por zona y hora (con incertidumbre), segmentación de zonas y una recomendación de cuántos taxis enviar, en una app de Streamlit que consulta su propia API.

**Entrega individual de:** Isaac Aníbal Pérez Pérez

## Enlaces

| Qué | Enlace |
|---|---|
| App (Streamlit Community Cloud) | _(link de tu app en Streamlit)_ |
| API (Render) | _(link de tu API en Render)_ — su documentación abre en `/docs` |
| Repositorio (GitHub) | _(link de tu repositorio)_ |

> La API está en el plan gratuito de Render: se duerme tras 15 minutos sin uso y tarda cerca de un minuto en despertar. La app lo explica con un mensaje si no responde.

## Qué hace

| Página de la app | Qué responde |
|---|---|
| **Pronóstico** | Cuántos viajes habrá cada hora en una zona, con su banda del 80 % y los viajes reales cuando existen |
| **Cuántos taxis enviar** | Según el costo de un taxi parado y de un pasajero perdido, el cuantil óptimo, los taxis por hora, la comparación de costos y un plan descargable |
| **Tipos de zona** | K-Means (k elegido con la silueta) y PCA: 4 grupos con nombre, filtros y selección de zonas |
| **Ficha del modelo** | Para qué sirve, cómo se evaluó, dónde falla y para qué no debe usarse |
| **Monitoreo del error** (extra) | Error día a día de la semana de prueba y alerta al pasar un límite |

## Estructura

```
taxis-nyc/
├── preparacion.ipynb            # datos, modelos y métricas (se trabaja en Colab)
├── ficha_modelo.md              # la ficha, generada por el cuaderno
├── api/
│   ├── main.py                  # la API (FastAPI)
│   ├── modelo_pronostico.ubj    # el modelo guardado con save_model
│   ├── demanda.parquet          # las horas del 25-ene al 1-feb con sus variables ya calculadas
│   └── requirements.txt
└── app/
    ├── streamlit_app.py         # punto de entrada: st.navigation
    ├── utils.py                 # conexión con la API, selectores y cálculos
    ├── paginas/                 # una página por archivo
    ├── data/                    # zonas segmentadas, métricas y error diario (salen del cuaderno)
    ├── .streamlit/config.toml   # el tema de colores
    └── requirements.txt
```

## La API

| Endpoint | Recibe | Devuelve |
|---|---|---|
| `GET /` | nada | que la API está en línea |
| `GET /info` | nada | zonas pronosticables, fechas disponibles y cuantiles |
| `GET /pronostico` | `zona_id` y `fecha` (AAAA-MM-DD) | las 24 horas, cada una con sus cuantiles (p10 a p90), el valor real (o `null`) y el de hace una semana |

Una zona o fecha que no existe responde `404` con un mensaje claro.

## Cómo correr el proyecto en la computadora

1. **Regenerar datos y modelo** (opcional; ya vienen en el repositorio): abrir `preparacion.ipynb` en Colab o Jupyter y ejecutar todo. Descarga los datos públicos de la NYC TLC y deja los archivos en `api/` y `app/data/`.
2. **API:**
   ```bash
   cd api
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
   Abrir http://localhost:8000/docs.
3. **App:**
   ```bash
   cd app
   pip install -r requirements.txt
   API_URL=http://localhost:8000 streamlit run streamlit_app.py
   ```

## Cómo se publicó

- **API en Render:** Web Service con el repositorio; Root Directory `api`; Build `pip install -r requirements.txt`; Start `uvicorn main:app --host 0.0.0.0 --port $PORT`; plan Free.
- **App en Streamlit Community Cloud:** mismo repositorio; Main file path `app/streamlit_app.py`; en Secrets: `API_URL = "https://<su-api>.onrender.com"` (sin `/` al final).

## Funciones avanzadas de Streamlit que usa

`st.navigation` + `st.Page`, `@st.fragment`, `@st.dialog`, `st.plotly_chart(on_select="rerun")`, `st.column_config` (barras, mini gráficos, formatos), `@st.cache_data`, `st.secrets`, `st.query_params`, `st.status`, `st.toast`, `st.pills`, `st.segmented_control`, `st.badge`, `st.popover`, `st.metric(chart_data=...)`, `st.feedback` y `.streamlit/config.toml`.

## Datos y reglas

Viajes de taxi amarillo de enero de 2024 (NYC TLC), zona de origen. Se pronostican las zonas con al menos 3,000 viajes y se segmentan las de al menos 500 (sin las zonas `Unknown`). Entrenamiento hasta el 24 de enero, prueba del 25 al 31 y pronóstico a futuro el 1 de febrero. Todas las cifras de la ficha salen del cuaderno.
