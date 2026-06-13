# Proyecto Churn MLOps

![CI](https://github.com/nicolas-madepa/proyecto_churn_mlops/actions/workflows/ci.yml/badge.svg)

Proyecto integrador de **ML-Ops**: una API predictiva de abandono de clientes (churn) construida, contenerizada y **operada** con observabilidad, alertas, integración continua y orquestación.

## Capacidades

- **Modelo** serializado y versionado (`modelo_churn_v1.joblib` + metadatos).
- **API** (FastAPI) con validación de entradas: `/`, `/health`, `/info`, `/predict`, `/selftest`, `/metrics`, `/docs`.
- **Docker**: imagen con `HEALTHCHECK` y `docker compose` que levanta todo el stack.
- **Monitoreo** en tiempo real con **Prometheus + Grafana** (dashboard provisionado como código).
- **Alertas** de Grafana provisionadas (modelo caído, latencia, errores 422).
- **CI** con GitHub Actions (pytest en cada push/PR).
- **Drift**: simulación demostrable observable en el dashboard.
- **Orquestación** con **Airflow** (DAGs de reentrenamiento, generación de tráfico y simulación de drift).

## Problema del proyecto

Se trabajará con un caso simplificado de predicción de abandono de clientes, conocido como churn.

El modelo intentará predecir si un cliente podría abandonar un servicio, utilizando variables como edad, antigüedad, saldo promedio, reclamos y uso de aplicación móvil.

## Estructura del proyecto

```text
proyecto_churn_mlops
├── api/                  # API FastAPI (instrumentada con Prometheus)
├── src/                  # preparar_datos / entrenar_modelo / evaluar_modelo
├── models/               # modelo serializado .joblib + metadatos
├── tests/                # pruebas automáticas (pytest)
├── dags/                 # DAGs de Airflow (reentrenamiento, tráfico, drift)
├── scripts/              # generar_trafico.py / simular_drift.py
├── monitoring/           # Prometheus + provisioning de Grafana (datasource, dashboard, alertas)
├── docs/                 # métricas del modelo
├── data/ · notebooks/
├── Dockerfile · Dockerfile.airflow · .dockerignore
├── docker-compose.yml    # API + Prometheus + Grafana + Airflow
├── .github/workflows/    # CI (GitHub Actions)
└── requirements.txt · README.md
```

## Carpetas principales

- `api`: API del modelo (endpoints, validación y métricas Prometheus).
- `src`: scripts del modelo (preparación, entrenamiento y evaluación).
- `models`: modelo serializado y sus metadatos.
- `tests`: pruebas automáticas.
- `dags`: DAGs de Airflow que orquestan el pipeline.
- `scripts`: utilidades para generar tráfico y simular drift.
- `monitoring`: configuración de Prometheus y los dashboards/alertas de Grafana.
- `docs`: documentación y métricas.

## Flujo inicial del proyecto

El flujo básico será:

1. Preparar los datos.
2. Entrenar el modelo.
3. Evaluar el modelo.
4. Guardar las métricas.
5. Crear una API básica.
6. Probar el funcionamiento inicial.

## API del servicio (FastAPI)

Levantar la API en local:

```bash
uvicorn api.main:app --reload
```

Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Mensaje de estado del servicio y autor. |
| GET | `/health` | Estado del servicio y disponibilidad del modelo. |
| GET | `/info` | Versión del modelo, autor, variables utilizadas y metadatos. |
| GET | `/selftest` | Ejecuta pruebas automáticas (modelo, predicción, validación) y expone su estado. |
| GET | `/metrics` | Métricas del servicio en formato Prometheus. |
| POST | `/predict` | Predice churn; devuelve probabilidad, nivel de riesgo y una recomendación. |

### Ejemplo de `POST /predict`

Cuerpo de la solicitud:

```json
{
  "edad": 28,
  "antiguedad_meses": 8,
  "saldo_promedio": 1200,
  "reclamos": 3,
  "usa_app": 0
}
```

Respuesta:

```json
{
  "churn_predicho": 1,
  "probabilidad_churn": 0.92,
  "nivel_riesgo": "alto",
  "recomendacion": "Alta probabilidad de abandono; priorizar contacto y oferta de retención.",
  "version_modelo": "v1",
  "autor": "Nicolás Oporto"
}
```

### Validaciones de entrada

`/predict` valida los rangos de cada campo (por ejemplo `edad` entre 18 y 100, `usa_app` en {0, 1}). Las solicitudes con campos faltantes, tipos incorrectos o valores fuera de rango devuelven un error `422`.

## Modelo y artefactos

El entrenamiento (`src/entrenar_modelo.py`) genera en `models/`:

- `modelo_churn_v1.joblib`: modelo serializado (versión v1).
- `modelo_churn_v1_metadata.json`: metadatos (autor, algoritmo, fecha de entrenamiento, variables).

y las métricas en `docs/metricas_modelo.md`.

## Monitoreo y operación (Prometheus + Grafana)

El servicio está instrumentado con **Prometheus** y se monitorea con **Grafana**, levantados junto a la API mediante `docker compose`.

### Levantar todo el stack

```bash
docker compose up -d --build
```

| Servicio | URL | Descripción |
|---|---|---|
| API | http://localhost:8005 | API de churn (`/`, `/health`, `/info`, `/predict`, `/docs`) |
| API · métricas | http://localhost:8005/metrics | Métricas en formato Prometheus |
| API · self-tests | http://localhost:8005/selftest | Pruebas automáticas en caliente |
| Prometheus | http://localhost:9091 | Recolección de métricas |
| Grafana | http://localhost:3001 | Dashboards (usuario/clave: `admin`/`admin`) |

El dashboard **"Churn API - Monitoreo ML-Ops"** se provisiona automáticamente y muestra: tasa de solicitudes, latencia p95 de `/predict`, errores 422, predicciones por nivel de riesgo, probabilidad promedio de churn, disponibilidad del modelo y estado de las pruebas automáticas.

### Métricas personalizadas (dominio ML)

- `churn_predicciones_total{nivel_riesgo}` — predicciones por nivel de riesgo.
- `churn_probabilidad_churn` — distribución de la probabilidad de churn predicha.
- `churn_errores_validacion_total` — solicitudes inválidas (HTTP 422).
- `churn_modelo_disponible` — 1/0 según disponibilidad del modelo.
- `churn_selftest_status{prueba}` — resultado de cada prueba automática.

### Generar tráfico para la demo / capturas

Para ver el dashboard actualizándose en tiempo real (y verificar el servicio en vivo, sin enviar predicciones a mano):

```bash
python scripts/generar_trafico.py            # continuo (Ctrl+C para detener)
python scripts/generar_trafico.py --n 50     # 50 solicitudes y termina
```

Envía predicciones válidas variadas e inválidas hacia el contenedor, y comprueba que respondan `200`/`422`.

### Alertas (Grafana)

Grafana incluye alertas provisionadas como código (`monitoring/grafana/provisioning/alerting/`):

- **Modelo de churn no disponible** (crítica) — se dispara si `churn_modelo_disponible < 1` o la API no responde.
- **Latencia p95 de /predict alta** — si supera 0.5 s de forma sostenida.
- **Pico de errores 422** — ante un aumento sostenido de solicitudes inválidas.

### Simular drift

Para demostrar *data drift* en vivo (en el dashboard se observa cómo sube la probabilidad de churn):

```bash
python scripts/simular_drift.py
```

Envía un lote "normal" y luego uno con la distribución desplazada (clientes de alto riesgo), y reporta el cambio en la probabilidad promedio.

## Integración continua (CI)

Cada push y cada Pull Request ejecutan las pruebas automáticamente con GitHub Actions (`.github/workflows/ci.yml`), garantizando que la API siga funcionando antes de integrar cambios.

## Orquestación con Airflow

Un servicio **Airflow local** (aislado, dentro del mismo `docker compose`) orquesta tres DAGs (`dags/`):

- **`churn_retraining`** — reentrenamiento: `preparar_datos → entrenar_modelo → evaluar_modelo`. Cierra el ciclo ML-Ops ante drift.
- **`churn_generar_trafico`** — genera tráfico hacia la API para poblar el dashboard de monitoreo.
- **`churn_simular_drift`** — simula data drift; el cambio se observa en vivo en Grafana.

```bash
docker compose up -d --build airflow
```

- UI de Airflow: http://localhost:8082 — **acceso sin login** (modo demo local: todos los usuarios son admin).
- Disparar un DAG: desde la UI (botón ▶) o con `docker exec airflow-oporto airflow dags trigger <dag_id>`.
