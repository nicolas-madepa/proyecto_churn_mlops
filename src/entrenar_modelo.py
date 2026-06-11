import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

AUTOR = "Nicolás Oporto"
MODEL_VERSION = "v1"

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

TRAIN_DATA = DATA_DIR / "train.csv"
MODEL_FILE = MODELS_DIR / f"modelo_churn_{MODEL_VERSION}.joblib"
METADATA_FILE = MODELS_DIR / f"modelo_churn_{MODEL_VERSION}_metadata.json"

def entrenar_modelo():
    """
    Entrena un modelo de clasificación para predecir churn, lo serializa con
    joblib y genera un archivo de metadatos para trazabilidad.
    """

    if not TRAIN_DATA.exists():
        raise FileNotFoundError(
            "No se encontró data/train.csv. Primero ejecuta src/preparar_datos.py"
        )

    MODELS_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(TRAIN_DATA)

    X = df.drop(columns=["churn"])
    y = df["churn"]

    modelo = Pipeline(
        steps=[
            ("escalado", StandardScaler()),
            ("clasificador", LogisticRegression())
        ]
    )

    modelo.fit(X, y)

    joblib.dump(modelo, MODEL_FILE)

    metadata = {
        "modelo": f"modelo_churn_{MODEL_VERSION}",
        "version": MODEL_VERSION,
        "autor": AUTOR,
        "algoritmo": "LogisticRegression + StandardScaler (Pipeline)",
        "framework": f"scikit-learn {sklearn.__version__}",
        "fecha_entrenamiento": datetime.now().isoformat(timespec="seconds"),
        "variables_predictoras": list(X.columns),
        "variable_objetivo": "churn",
        "n_muestras_entrenamiento": int(len(df)),
        "archivo_modelo": MODEL_FILE.name,
    }

    METADATA_FILE.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Modelo entrenado correctamente.")
    print(f"Modelo guardado en: {MODEL_FILE}")
    print(f"Metadatos guardados en: {METADATA_FILE}")

if __name__ == "__main__":
    entrenar_modelo()
