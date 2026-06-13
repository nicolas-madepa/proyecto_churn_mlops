"""
Simulación de DATA DRIFT contra la API en vivo.

Envía dos lotes de solicitudes a /predict y compara la probabilidad de churn:
  1) Lote BASE: clientes de un perfil "normal" (variado).
  2) Lote DERIVADO (drift): clientes de un perfil desplazado (jóvenes, baja
     antigüedad, saldo bajo, muchos reclamos, sin app) -> mayor riesgo de churn.

El cambio se observa EN VIVO en el dashboard de Grafana: sube la probabilidad
promedio de churn y se dispara la franja de nivel de riesgo "alto".

Importante: una entrada atípica aislada NO es drift; el drift es un cambio
SOSTENIDO en la distribución de entrada, que es justo lo que simula este lote.

Uso:
  python scripts/simular_drift.py
  python scripts/simular_drift.py --url http://localhost:8005 --n 40 --delay 0.3
"""
import argparse
import json
import random
import time
import urllib.request


def predecir(url, cliente):
    data = json.dumps(cliente).encode("utf-8")
    req = urllib.request.Request(
        url + "/predict", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def cliente_base():
    """Perfil normal y variado."""
    return {
        "edad": random.randint(30, 60),
        "antiguedad_meses": random.randint(18, 72),
        "saldo_promedio": random.randint(2500, 8000),
        "reclamos": random.randint(0, 2),
        "usa_app": 1,
    }


def cliente_derivado():
    """Perfil desplazado (data drift) hacia clientes de alto riesgo de churn."""
    return {
        "edad": random.randint(18, 28),
        "antiguedad_meses": random.randint(1, 8),
        "saldo_promedio": random.randint(500, 1500),
        "reclamos": random.randint(4, 6),
        "usa_app": 0,
    }


def ejecutar_lote(url, generador, n, delay, etiqueta):
    print(f"\n=== Lote {etiqueta} ({n} solicitudes) ===")
    probs = []
    for i in range(n):
        r = predecir(url, generador())
        if r and r.get("probabilidad_churn") is not None:
            probs.append(r["probabilidad_churn"])
            print(f"  [{i+1:3d}] prob_churn={r['probabilidad_churn']:.3f}  nivel={r['nivel_riesgo']}")
        time.sleep(delay)
    prom = sum(probs) / len(probs) if probs else 0.0
    print(f"  -> Probabilidad promedio de churn en el lote {etiqueta}: {prom:.3f}")
    return prom


def main():
    ap = argparse.ArgumentParser(description="Simula data drift y lo hace visible en el dashboard.")
    ap.add_argument("--url", default="http://localhost:8005")
    ap.add_argument("--n", type=int, default=30, help="solicitudes por lote")
    ap.add_argument("--delay", type=float, default=0.3, help="segundos entre solicitudes")
    args = ap.parse_args()

    print(f"Simulando data drift contra {args.url}")
    print("Abre el dashboard de Grafana para ver el cambio en tiempo real.")

    prom_base = ejecutar_lote(args.url, cliente_base, args.n, args.delay, "BASE (normal)")
    prom_drift = ejecutar_lote(args.url, cliente_derivado, args.n, args.delay, "DERIVADO (drift)")

    print("\n--- Resultado de la simulación ---")
    print(f"  Probabilidad promedio  BASE:     {prom_base:.3f}")
    print(f"  Probabilidad promedio  DERIVADO: {prom_drift:.3f}")
    delta = prom_drift - prom_base
    print(f"  Cambio (drift):                  {delta:+.3f}")
    if delta > 0.15:
        print("  -> Drift evidente: el desplazamiento de la distribución de entrada elevó")
        print("     la probabilidad de churn de forma sostenida. Señal para evaluar reentrenamiento.")
    else:
        print("  -> Cambio leve; repite con más solicitudes para acentuar el efecto.")


if __name__ == "__main__":
    main()
