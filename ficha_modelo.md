# Ficha del modelo: pronóstico de viajes de taxi por zona y hora

## Para qué sirve
Pronostica cuántos viajes de taxi amarillo habrá **por hora y por zona** de Nueva York el día siguiente, con un rango de incertidumbre (cuantiles de 10 % a 90 %), para decidir cuántos taxis enviar a cada zona.

## Con qué datos se entrenó
Viajes de taxi amarillo de enero de 2024 (NYC TLC): 2,964,606 viajes válidos. Se pronostican 58 zonas con al menos 3,000 viajes en el mes. Entrenamiento: del 8 al 24 de enero (la primera semana solo sirve para calcular los valores pasados de cada hora). Prueba: del 25 al 31 de enero.

## Cómo se evaluó
Por tiempo, nunca al azar: se entrena con el pasado y se prueba con la semana siguiente. Variables: valores de hace 24, 48 y 168 horas (nunca menos de 24: así no hay fuga de datos), promedio del día anterior, hora, día de la semana, feriado y zona. Modelo: XGBoost con 9 cuantiles; hiperparámetros elegidos con la semana de validación (18 al 24 de enero): {'n_estimators': 500, 'max_depth': 5, 'learning_rate': 0.1}.

## Qué tan bien funciona
| | Error (WAPE) | Error (viajes por hora) |
|---|---|---|
| Modelo (mediana) | 16.4% | 11.6 |
| Igual que hace una semana | 16.8% | 11.9 |
| Igual que ayer | 30.1% | 21.3 |

El modelo le gana a «igual que hace una semana» por 0.4 puntos porcentuales: una ventaja pequeña. Por día, gana en 5 de 7 días de la semana de prueba. **Su valor está en el rango de incertidumbre**, que la regla simple no da: el rango del 80 % (de p10 a p90) cubre el **80.8%** de las horas reales, cuando debería cubrir cerca del 80 %.

Con costos de USD 40 por pasajero perdido y USD 10 por taxi ocioso (cuantil óptimo 0.80), enviar el cuantil recomendado cuesta USD 2,219,390 en la semana de prueba, contra USD 2,831,730 del pronóstico central (22% menos) y USD 3,160,950 de «igual que hace una semana» (30% menos).

## Dónde se equivoca más
- Por tipo de zona, el error es mayor en **«Barrios residenciales de baja demanda»** (38.2%, solo 3 zonas pronosticadas, con unos 6 viajes por hora: con pocos viajes el ruido pesa más) y menor en **«Centro de alta demanda»** (15.9%, 44 zonas).
- Por día, el peor fue el **2024-01-28** (21.3%). Días sobre el límite de alerta (27.6%): ninguno.

## Limitaciones y usos no recomendados
- Solo hay **un mes** de datos: no ve estacionalidad anual, clima, eventos ni obras. Un evento fuera de lo normal (nevada, concierto, huelga) no está en el modelo.
- Solo cubre **taxis amarillos** y las **58 zonas** con al menos 3,000 viajes; hay 42 zonas más (con 500 a 2,999 viajes) que se segmentan pero **no se pronostican**, y en total 200 zonas con viajes quedan sin pronóstico.
- Se supone que un taxi atiende un viaje por hora; en la realidad un viaje dura más o menos de una hora.
- El pronóstico mide **viajes que se realizaron**, no la demanda real: donde faltan taxis, la demanda no atendida no aparece en los datos.
- **No usar** para recortar el servicio en barrios con pocos viajes de taxi amarillo: el modelo puede subestimar la demanda de zonas con transporte público deficiente o donde la gente usa otros servicios, y quienes viven ahí (a menudo con menos alternativas) serían los perjudicados. Tampoco para evaluar a conductores ni para decisiones de precios.
