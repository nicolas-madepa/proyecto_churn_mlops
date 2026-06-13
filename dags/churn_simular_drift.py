"""
DAG para simular data drift contra la API.

Ejecuta scripts/simular_drift.py contra el servicio de la API en la red de
docker-compose (http://churn-api:8000): envía un lote "normal" y luego uno con
la distribución desplazada (clientes de alto riesgo). El cambio en la
probabilidad promedio de churn se observa en vivo en el dashboard de Grafana.
"""
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

PROYECTO = "/opt/proyecto"
API_URL = "http://churn-api:8000"  # nombre del servicio de la API en docker-compose

with DAG(
    dag_id="churn_simular_drift",
    description="Simula data drift hacia la API; el cambio se observa en el dashboard.",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["churn", "mlops", "drift"],
) as dag:

    simular_drift = BashOperator(
        task_id="simular_drift",
        bash_command=f"python {PROYECTO}/scripts/simular_drift.py --url {API_URL} --n 30 --delay 0.2",
    )
