import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

AUTOR = "Nicolás Oporto"
MODEL_VERSION = "v1"

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_FILE = BASE_DIR / "models" / f"modelo_churn_{MODEL_VERSION}.joblib"
METADATA_FILE = BASE_DIR / "models" / f"modelo_churn_{MODEL_VERSION}_metadata.json"

VARIABLES = ["edad", "antiguedad_meses", "saldo_promedio", "reclamos", "usa_app"]

app = FastAPI(
    title="Servicio ML-Ops - Churn",
    version="1.0.0",
    description=(
        "API predictiva de abandono de clientes (churn) con validación de "
        "entradas, metadatos del modelo, endpoint informativo, pruebas "
        "automáticas (/selftest) y métricas para Prometheus/Grafana (/metrics)."
    ),
)

# --------------------------------------------------------------------------
# Métricas Prometheus de dominio (ML). Las métricas HTTP (latencia, tasa de
# solicitudes, códigos de estado) las agrega automáticamente el Instrumentator.
# --------------------------------------------------------------------------
PREDICCIONES = Counter(
    "churn_predicciones_total", "Predicciones realizadas por nivel de riesgo", ["nivel_riesgo"]
)
PROBABILIDAD = Histogram(
    "churn_probabilidad_churn", "Distribución de la probabilidad de churn predicha",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)
ERRORES_VALIDACION = Counter(
    "churn_errores_validacion_total", "Solicitudes rechazadas por validación (HTTP 422)"
)
MODELO_DISPONIBLE = Gauge(
    "churn_modelo_disponible", "1 si el modelo está cargado/presente, 0 en caso contrario"
)
SELFTEST = Gauge(
    "churn_selftest_status", "Resultado de cada prueba automática (1=ok, 0=falla)", ["prueba"]
)

# Instrumentación HTTP automática y exposición del endpoint /metrics
Instrumentator().instrument(app).expose(app)

MODELO_DISPONIBLE.set(1 if MODEL_FILE.exists() else 0)


class Cliente(BaseModel):
    edad: int = Field(..., ge=18, le=100, description="Edad del cliente (18 a 100).")
    antiguedad_meses: int = Field(..., ge=0, le=600, description="Antigüedad en meses (0 a 600).")
    saldo_promedio: float = Field(..., ge=0, description="Saldo promedio (mayor o igual a 0).")
    reclamos: int = Field(..., ge=0, le=50, description="Cantidad de reclamos (0 a 50).")
    usa_app: int = Field(..., ge=0, le=1, description="Usa la app móvil: 0 (no) o 1 (sí).")


@app.exception_handler(RequestValidationError)
async def manejar_validacion(request: Request, exc: RequestValidationError):
    """Cuenta las solicitudes inválidas (422) para monitoreo y responde el detalle."""
    ERRORES_VALIDACION.inc()
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


def cargar_modelo():
    """Carga el modelo serializado si existe."""
    if not MODEL_FILE.exists():
        return None
    return joblib.load(MODEL_FILE)


def cargar_metadata():
    """Carga los metadatos del modelo si existen."""
    if not METADATA_FILE.exists():
        return None
    return json.loads(METADATA_FILE.read_text(encoding="utf-8"))


def evaluar_riesgo(probabilidad):
    """Traduce la probabilidad de churn a un nivel de riesgo y una recomendación."""
    if probabilidad is None:
        return "desconocido", "No fue posible estimar la probabilidad de abandono."
    if probabilidad < 0.4:
        return "bajo", "Baja probabilidad de abandono; mantener seguimiento estándar."
    if probabilidad < 0.7:
        return "medio", "Riesgo moderado; considerar acciones de retención preventivas."
    return "alto", "Alta probabilidad de abandono; priorizar contacto y oferta de retención."


@app.get("/")
def inicio():
    return {
        "mensaje": "Servicio ML-Ops activo",
        "estado": "ok",
        "autor": AUTOR,
    }


@app.get("/health")
def health():
    disponible = MODEL_FILE.exists()
    MODELO_DISPONIBLE.set(1 if disponible else 0)
    return {
        "estado": "ok",
        "modelo_disponible": disponible,
        "version_modelo": MODEL_VERSION,
    }


@app.get("/info")
def info():
    """Endpoint informativo: versión del modelo, autor y variables utilizadas."""
    return {
        "servicio": "API de predicción de churn",
        "autor": AUTOR,
        "version_modelo": MODEL_VERSION,
        "modelo_disponible": MODEL_FILE.exists(),
        "variables_utilizadas": VARIABLES,
        "metadata_modelo": cargar_metadata(),
    }


@app.get("/selftest")
def selftest():
    """Ejecuta pruebas automáticas contra la propia API y expone su estado a Prometheus."""
    resultados = {}

    modelo = cargar_modelo()
    resultados["modelo_cargado"] = modelo is not None

    ok_pred = False
    if modelo is not None:
        try:
            datos = pd.DataFrame([
                {"edad": 35, "antiguedad_meses": 24, "saldo_promedio": 3500, "reclamos": 0, "usa_app": 1}
            ])
            modelo.predict(datos)
            ok_pred = True
        except Exception:
            ok_pred = False
    resultados["prediccion_valida"] = ok_pred

    try:
        Cliente(edad=5, antiguedad_meses=8, saldo_promedio=1200, reclamos=3, usa_app=0)
        resultados["validacion_rango"] = False
    except ValidationError:
        resultados["validacion_rango"] = True

    resultados["metadata_disponible"] = cargar_metadata() is not None

    for prueba, ok in resultados.items():
        SELFTEST.labels(prueba=prueba).set(1 if ok else 0)

    return {"todas_ok": all(resultados.values()), "pruebas": resultados}


@app.post("/predict")
def predict(cliente: Cliente):
    modelo = cargar_modelo()

    if modelo is None:
        raise HTTPException(
            status_code=503,
            detail="El modelo aún no está disponible. Primero se debe entrenar el modelo.",
        )

    datos = pd.DataFrame([cliente.model_dump()])

    prediccion = int(modelo.predict(datos)[0])

    probabilidad = None
    if hasattr(modelo, "predict_proba"):
        probabilidad = float(modelo.predict_proba(datos)[0][1])

    nivel_riesgo, recomendacion = evaluar_riesgo(probabilidad)

    PREDICCIONES.labels(nivel_riesgo=nivel_riesgo).inc()
    if probabilidad is not None:
        PROBABILIDAD.observe(probabilidad)

    return {
        "churn_predicho": prediccion,
        "probabilidad_churn": probabilidad,
        "nivel_riesgo": nivel_riesgo,
        "recomendacion": recomendacion,
        "version_modelo": MODEL_VERSION,
        "autor": AUTOR,
    }
