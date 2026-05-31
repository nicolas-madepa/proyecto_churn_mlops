# Instrucciones de ejecución

Pasos para ejecutar el proyecto de predicción de churn desde cero.

## 1. Crear y activar el entorno virtual

Desde la carpeta raíz del proyecto (`proyecto_churn_mlops`):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
```

La terminal debe mostrar el prefijo `(.venv)`.

## 2. Instalar dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Ejecutar el flujo del modelo

Ejecutar los scripts en orden:

```powershell
python src\preparar_datos.py
python src\entrenar_modelo.py
python src\evaluar_modelo.py
```

Esto genera automáticamente:

```text
data/churn_clientes.csv
data/train.csv
data/test.csv
models/modelo_churn.pkl
docs/metricas_modelo.md
```

## 4. Ejecutar la API

```powershell
uvicorn api.main:app --reload
```

Abrir en el navegador:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs (documentación interactiva Swagger)

Ejemplo de cuerpo para `POST /predict`:

```json
{
  "edad": 28,
  "antiguedad_meses": 8,
  "saldo_promedio": 1200,
  "reclamos": 3,
  "usa_app": 0
}
```

## 5. Ejecutar las pruebas automáticas

Detener la API con `Ctrl + C` y ejecutar:

```powershell
pytest
```
