from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

def test_inicio():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert "mensaje" in body
    assert "autor" in body

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert "estado" in body
    assert "modelo_disponible" in body

def test_info():
    response = client.get("/info")

    assert response.status_code == 200
    body = response.json()
    assert "autor" in body
    assert "version_modelo" in body
    assert "variables_utilizadas" in body

def test_predict_campo_faltante():
    # Falta el campo 'usa_app' -> error de validación 422
    cliente_incompleto = {
        "edad": 28,
        "antiguedad_meses": 8,
        "saldo_promedio": 1200,
        "reclamos": 3,
    }
    response = client.post("/predict", json=cliente_incompleto)

    assert response.status_code == 422

def test_predict_fuera_de_rango():
    # Edad fuera del rango permitido (18-100) -> error de validación 422
    cliente_invalido = {
        "edad": 5,
        "antiguedad_meses": 8,
        "saldo_promedio": 1200,
        "reclamos": 3,
        "usa_app": 0,
    }
    response = client.post("/predict", json=cliente_invalido)

    assert response.status_code == 422

def test_selftest():
    response = client.get("/selftest")

    assert response.status_code == 200
    body = response.json()
    assert "todas_ok" in body
    assert "pruebas" in body

def test_metrics():
    # El endpoint /metrics expone las métricas en formato Prometheus
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
