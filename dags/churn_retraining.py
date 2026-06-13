"""
DAG de reentrenamiento del modelo de churn (Apache Airflow).

Orquesta el pipeline de ML que cierra el ciclo ML-Ops: cuando el monitoreo
detecta drift (caída de calidad o cambio sostenido en la distribución), se
ejecuta este DAG para volver a preparar los datos, reentrenar y reevaluar el
modelo, dejándolo listo para publicar una nueva versión.

Pasos: preparar_datos -> entrenar_modelo -> evaluar_modelo.
Se dispara manualmente (o se podría agendar / disparar ante una alerta de drift).
"""
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

# El código del proyecto se incluye en la imagen de Airflow en /opt/proyecto.
PROYECTO = "/opt/proyecto"

with DAG(
    dag_id="churn_retraining",
    description="Reentrenamiento del modelo de churn: preparar -> entrenar -> evaluar.",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["churn", "mlops", "retraining"],
) as dag:

    preparar_datos = BashOperator(
        task_id="preparar_datos",
        bash_command=f"python {PROYECTO}/src/preparar_datos.py",
    )

    entrenar_modelo = BashOperator(
        task_id="entrenar_modelo",
        bash_command=f"python {PROYECTO}/src/entrenar_modelo.py",
    )

    evaluar_modelo = BashOperator(
        task_id="evaluar_modelo",
        bash_command=f"python {PROYECTO}/src/evaluar_modelo.py",
    )

    preparar_datos >> entrenar_modelo >> evaluar_modelo
