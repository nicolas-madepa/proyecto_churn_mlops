"""
DAG para generar tráfico hacia la API (poblar el dashboard de monitoreo).

Ejecuta scripts/generar_trafico.py contra el servicio de la API en la red de
docker-compose (http://churn-api:8000). Útil para demos y capturas: dispara el
DAG y el dashboard de Grafana cobra vida con solicitudes válidas e inválidas.
"""
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

PROYECTO = "/opt/proyecto"
API_URL = "http://churn-api:8000"  # nombre del servicio de la API en docker-compose

with DAG(
    dag_id="churn_generar_trafico",
    description="Genera tráfico hacia la API para poblar el dashboard de monitoreo.",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["churn", "mlops", "monitoreo"],
) as dag:

    generar_trafico = BashOperator(
        task_id="generar_trafico",
        bash_command=f"python {PROYECTO}/scripts/generar_trafico.py --url {API_URL} --n 80 --delay 0.2",
    )
