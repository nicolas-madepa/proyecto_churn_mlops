"""
Generador de tráfico y prueba automatizada del servicio en vivo.

Envía solicitudes HTTP reales a la API que corre en el contenedor, de modo que
las métricas se actualicen en Prometheus/Grafana en tiempo real. Sirve para:
  - poblar el dashboard de monitoreo durante una demo o para capturas;
  - verificar el servicio en caliente (válida -> 200, inválida -> 422).

Uso:
  python scripts/generar_trafico.py                 # infinito (Ctrl+C para parar)
  python scripts/generar_trafico.py --n 50          # 50 iteraciones y termina
  python scripts/generar_trafico.py --url http://localhost:8005 --delay 0.3 --invalidas 0.25

Solo usa la librería estándar (no requiere dependencias extra).
"""
import argparse
import json
import random
import time
import urllib.error
import urllib.request


def _post(url, path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


def _get(url, path):
    try:
        with urllib.request.urlopen(url + path, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def cliente_valido():
    """Perfil de cliente válido y aleatorio (genera distintos niveles de riesgo)."""
    return {
        "edad": random.randint(18, 70),
        "antiguedad_meses": random.randint(1, 72),
        "saldo_promedio": random.randint(500, 8000),
        "reclamos": random.randint(0, 6),
        "usa_app": random.randint(0, 1),
    }


def cliente_invalido():
    """Devuelve una solicitud inválida de algún tipo (debe responder 422)."""
    return random.choice([
        {"edad": 5, "antiguedad_meses": 8, "saldo_promedio": 1200, "reclamos": 3, "usa_app": 0},   # fuera de rango
        {"edad": 30, "antiguedad_meses": 8, "saldo_promedio": 1200, "reclamos": 3},                # campo faltante
        {"edad": "treinta", "antiguedad_meses": 8, "saldo_promedio": 1200, "reclamos": 3, "usa_app": 0},  # tipo incorrecto
    ])


def main():
    ap = argparse.ArgumentParser(description="Genera tráfico y verifica la API en vivo.")
    ap.add_argument("--url", default="http://localhost:8005", help="URL base de la API")
    ap.add_argument("--n", type=int, default=0, help="iteraciones (0 = infinito)")
    ap.add_argument("--delay", type=float, default=0.5, help="segundos entre solicitudes")
    ap.add_argument("--invalidas", type=float, default=0.2, help="proporción de inválidas (0-1)")
    args = ap.parse_args()

    print(f"Generando tráfico hacia {args.url}  (Ctrl+C para detener)\n")
    cont = {"validas_ok": 0, "validas_mal": 0, "invalidas_ok": 0, "invalidas_mal": 0, "selftest": 0}
    i = 0
    try:
        while args.n == 0 or i < args.n:
            i += 1
            if random.random() < args.invalidas:
                code, _ = _post(args.url, "/predict", cliente_invalido())
                if code == 422:
                    cont["invalidas_ok"] += 1
                    estado = f"INVALIDA -> {code} OK"
                else:
                    cont["invalidas_mal"] += 1
                    estado = f"INVALIDA -> {code} (se esperaba 422!)"
            else:
                code, body = _post(args.url, "/predict", cliente_valido())
                nivel = body.get("nivel_riesgo") if body else "?"
                if code == 200:
                    cont["validas_ok"] += 1
                    estado = f"valida   -> 200 ({nivel})"
                else:
                    cont["validas_mal"] += 1
                    estado = f"valida   -> {code} (se esperaba 200!)"
            if i % 10 == 0:
                if _get(args.url, "/selftest") == 200:
                    cont["selftest"] += 1
            print(f"[{i:4d}] {estado}")
            time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\n(detenido por el usuario)")

    print("\n--- Resumen ---")
    print(f"  Válidas correctas (200):   {cont['validas_ok']}")
    print(f"  Inválidas correctas (422): {cont['invalidas_ok']}")
    print(f"  Llamadas a /selftest:      {cont['selftest']}")
    fallos = cont["validas_mal"] + cont["invalidas_mal"]
    if fallos == 0:
        print("  Resultado: OK — el servicio respondió como se esperaba en todas las solicitudes.")
    else:
        print(f"  Resultado: ATENCIÓN — {fallos} respuesta(s) no fueron las esperadas.")


if __name__ == "__main__":
    main()
