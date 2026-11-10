"""API de pronóstico de viajes de taxi por zona y hora (Taxis NYC).

Endpoints:
    GET /            -> la API está en línea
    GET /info        -> zonas pronosticables, fechas disponibles y cuantiles
    GET /pronostico  -> las 24 horas de una zona y fecha, con sus cuantiles

La API NO recalcula variables: `demanda.parquet` trae las horas del 25 de enero al 1 de febrero con sus
variables ya calculadas (en el cuaderno); aquí solo se busca la zona y la fecha y se predice.
"""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException

CARPETA = Path(__file__).parent
CUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
VARIABLES = ["lag_24", "lag_48", "lag_167", "lag_168", "lag_169", "media_dia_ant",
             "hora_dia", "dia_semana", "feriado", "zona"]
DIA_SIN_DATOS_REALES = date(2024, 2, 1)   # el "mañana": solo hay pronóstico

# El modelo se carga con xgboost.Booster: así la API no necesita scikit-learn.
modelo = xgb.Booster()
modelo.load_model(CARPETA / "modelo_pronostico.ubj")

demanda = pd.read_parquet(CARPETA / "demanda.parquet")
ZONAS = sorted(int(z) for z in demanda["PULocationID"].unique())
# La zona debe ser una categoría con las MISMAS categorías (y el mismo tipo, entero) que en el entrenamiento.
demanda["zona"] = pd.Categorical(demanda["PULocationID"], categories=ZONAS)
demanda["fecha"] = demanda["hora"].dt.date
FECHAS = sorted(demanda["fecha"].unique())

app = FastAPI(title="API de pronóstico de taxis NYC", version="1.0")


@app.get("/")
def raiz():
    return {"estado": "en línea", "servicio": "pronóstico de viajes de taxi por zona y hora"}


@app.get("/info")
def info():
    zonas = (demanda.drop_duplicates("PULocationID")[["PULocationID", "zona_nombre", "distrito"]]
             .sort_values("PULocationID"))
    return {
        "zonas": [{"id": int(f.PULocationID), "nombre": f.zona_nombre, "distrito": f.distrito} for f in zonas.itertuples()],
        "fechas": [f.isoformat() for f in FECHAS],
        "fecha_sin_datos_reales": DIA_SIN_DATOS_REALES.isoformat(),
        "cuantiles": CUANTILES,
    }


@app.get("/pronostico")
def pronostico(zona_id: int, fecha: date):
    filas = demanda[(demanda["PULocationID"] == zona_id) & (demanda["fecha"] == fecha)].sort_values("hora")
    if filas.empty:
        raise HTTPException(status_code=404, detail="No hay datos para esa zona o fecha")

    predicciones = np.sort(modelo.predict(xgb.DMatrix(filas[VARIABLES], enable_categorical=True)), axis=1)  # evita cuantiles cruzados
    horas = []
    for (_, fila), cuantiles in zip(filas.iterrows(), predicciones):
        horas.append({
            "hora": int(fila["hora_dia"]),
            "real": None if pd.isna(fila["viajes"]) else int(fila["viajes"]),
            "hace_una_semana": int(fila["lag_168"]),
            "cuantiles": {f"p{int(round(q * 100))}": round(float(v), 1) for q, v in zip(CUANTILES, cuantiles)},
        })
    primera = filas.iloc[0]
    return {
        "zona": {"id": int(zona_id), "nombre": primera["zona_nombre"], "distrito": primera["distrito"]},
        "fecha": fecha.isoformat(),
        "horas": horas,
    }
