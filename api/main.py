import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
        "entradas, metadatos del modelo y endpoint informativo."
    ),
)


class Cliente(BaseModel):
    edad: int = Field(..., ge=18, le=100, description="Edad del cliente (18 a 100).")
    antiguedad_meses: int = Field(..., ge=0, le=600, description="Antigüedad en meses (0 a 600).")
    saldo_promedio: float = Field(..., ge=0, description="Saldo promedio (mayor o igual a 0).")
    reclamos: int = Field(..., ge=0, le=50, description="Cantidad de reclamos (0 a 50).")
    usa_app: int = Field(..., ge=0, le=1, description="Usa la app móvil: 0 (no) o 1 (sí).")


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
    return {
        "estado": "ok",
        "modelo_disponible": MODEL_FILE.exists(),
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

    return {
        "churn_predicho": prediccion,
        "probabilidad_churn": probabilidad,
        "nivel_riesgo": nivel_riesgo,
        "recomendacion": recomendacion,
        "version_modelo": MODEL_VERSION,
        "autor": AUTOR,
    }
