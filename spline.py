"""
spline.py — Lógica de interpolación de Splines Cúbicos
=======================================================
Módulo independiente de Flask. Contiene:
  - Datos originales de demanda (horas → minutos)
  - Interpolación con CubicSpline (1440 valores)
  - Cálculo de T_espera = demanda / NUM_TAXIS
  - Funciones de acceso para la app Flask
"""

import numpy as np
from scipy.interpolate import CubicSpline, BarycentricInterpolator

# ── Constantes ─────────────────────────────────────────────────────────────
NUM_TAXIS = 200  # flota disponible (denominador de T_espera)

# ── Datos originales (horas, solicitudes/minuto) ───────────────────────────
# El punto (24.0, 0.0) es 00:00 del día siguiente, no se duplica
DATOS_RAW = [
    (0.0,   15.0),
    (1.5,   18.0),
    (3.0,   12.0),
    (6.0,   45.0),
    (9.0,  120.0),
    (12.0, 180.0),
    (15.0, 150.0),
    (18.0,  98.0),
    (19.5,  75.0),
    (21.0,  55.0),
    (24.0,   0.0),
]

# ── Conversión horas → minutos ─────────────────────────────────────────────
_horas   = np.array([d[0] for d in DATOS_RAW])
_demanda = np.array([d[1] for d in DATOS_RAW])
_minutos = _horas * 60   # 0.0 … 1440.0

# ── CubicSpline (condición "not-a-knot" por defecto) ──────────────────────
_cs = CubicSpline(_minutos, _demanda)

# ── Lagrange en forma baricéntrica (numéricamente más estable) ─────────────
_lagrange = BarycentricInterpolator(_minutos, _demanda)

# ── Evaluación en cada uno de los 1440 minutos del día ────────────────────
_x = np.arange(0, 1441)        # 0, 1, 2, …, 1440
_y = _cs(_x)                   # demanda interpolada por minuto
_y_lagrange = _lagrange(_x)

# Clipear valores negativos que puedan surgir en extremos del spline
_y = np.clip(_y, 0, None)
_y_lagrange = np.clip(_y_lagrange, 0, None)


def _hora_str(minuto: int) -> str:
    """Convierte un minuto del día a formato HH:MM."""
    hh, mm = divmod(minuto, 60)
    return f"{hh:02d}:{mm:02d}"


# ══════════════════════════════════════════════════════════════════════════
#  Funciones públicas
# ══════════════════════════════════════════════════════════════════════════

def get_puntos_control() -> list[dict]:
    """
    Devuelve los puntos de control originales como lista de dicts.

    Ejemplo de un elemento:
        {"hora": 0.0, "minuto": 0, "demanda": 15.0}
    """
    return [
        {
            "hora":    float(h),
            "minuto":  int(h * 60),
            "demanda": float(d),
        }
        for h, d in DATOS_RAW
    ]


def get_spline_completo() -> list[dict]:
    """
    Devuelve los 1441 puntos interpolados (minuto 0 … 1440).

    Cada elemento:
        {
          "minuto":   int,    # 0 … 1440
          "hora_str": "HH:MM",
          "demanda":  float,  # solicitudes/minuto  (≥ 0)
          "t_espera": float,  # minutos de espera = demanda / NUM_TAXIS
        }
    """
    resultado = []
    for x, y in zip(_x.tolist(), _y.tolist()):
        resultado.append({
            "minuto":   int(x),
            "hora_str": _hora_str(int(x)),
            "demanda":  round(float(y), 4),
            "t_espera": round(float(y) / NUM_TAXIS, 6),
        })
    return resultado


def get_lagrange_completo() -> list[dict]:
    """
    Devuelve los 1441 puntos interpolados con Lagrange (baricéntrico).

    Cada elemento:
        {
          "minuto":   int,
          "hora_str": "HH:MM",
          "demanda":  float,
          "t_espera": float,
        }
    """
    resultado = []
    for x, y in zip(_x.tolist(), _y_lagrange.tolist()):
        resultado.append({
            "minuto":   int(x),
            "hora_str": _hora_str(int(x)),
            "demanda":  round(float(y), 4),
            "t_espera": round(float(y) / NUM_TAXIS, 6),
        })
    return resultado


def get_comparativa_modelos() -> dict:
    """
    Compara Spline Cúbico vs Lagrange con métricas de error.

    Métrica principal: RMSE con validación cruzada leave-one-out (LOOCV)
    sobre los puntos de control para evitar error cero trivial en nodos.
    """
    # Error de ajuste directo en nodos (debe ser cercano a 0 en ambos)
    spline_nodos = _cs(_minutos)
    lag_nodos = _lagrange(_minutos)

    err_nodos_spline = spline_nodos - _demanda
    err_nodos_lagrange = lag_nodos - _demanda

    rmse_nodos_spline = float(np.sqrt(np.mean(err_nodos_spline ** 2)))
    rmse_nodos_lagrange = float(np.sqrt(np.mean(err_nodos_lagrange ** 2)))

    # LOOCV por cada punto de control
    errores_loocv = []
    for i in range(len(_minutos)):
        mask = np.arange(len(_minutos)) != i
        x_train = _minutos[mask]
        y_train = _demanda[mask]

        modelo_spline = CubicSpline(x_train, y_train)
        modelo_lagrange = BarycentricInterpolator(x_train, y_train)

        x_test = float(_minutos[i])
        y_real = float(_demanda[i])

        y_pred_spline = float(max(0.0, modelo_spline(x_test)))
        y_pred_lagrange = float(max(0.0, modelo_lagrange(x_test)))

        err_spline = y_pred_spline - y_real
        err_lagrange = y_pred_lagrange - y_real

        errores_loocv.append({
            "minuto": int(_minutos[i]),
            "hora_str": _hora_str(int(_minutos[i])),
            "valor_real": round(y_real, 4),
            "pred_spline": round(y_pred_spline, 4),
            "pred_lagrange": round(y_pred_lagrange, 4),
            "error_spline": round(float(err_spline), 6),
            "error_lagrange": round(float(err_lagrange), 6),
            "abs_error_spline": round(float(abs(err_spline)), 6),
            "abs_error_lagrange": round(float(abs(err_lagrange)), 6),
        })

    arr_err_s = np.array([e["error_spline"] for e in errores_loocv], dtype=float)
    arr_err_l = np.array([e["error_lagrange"] for e in errores_loocv], dtype=float)

    rmse_loocv_spline = float(np.sqrt(np.mean(arr_err_s ** 2)))
    rmse_loocv_lagrange = float(np.sqrt(np.mean(arr_err_l ** 2)))
    mae_loocv_spline = float(np.mean(np.abs(arr_err_s)))
    mae_loocv_lagrange = float(np.mean(np.abs(arr_err_l)))

    mejor_modelo = "Spline Cúbico" if rmse_loocv_spline <= rmse_loocv_lagrange else "Lagrange"

    idx_peor_s = int(np.argmax(np.abs(arr_err_s)))
    idx_peor_l = int(np.argmax(np.abs(arr_err_l)))

    return {
        "metodologia": "LOOCV sobre 11 puntos de control",
        "rmse_nodos": {
            "spline": round(rmse_nodos_spline, 8),
            "lagrange": round(rmse_nodos_lagrange, 8),
        },
        "rmse_loocv": {
            "spline": round(rmse_loocv_spline, 6),
            "lagrange": round(rmse_loocv_lagrange, 6),
        },
        "mae_loocv": {
            "spline": round(mae_loocv_spline, 6),
            "lagrange": round(mae_loocv_lagrange, 6),
        },
        "mejor_modelo": mejor_modelo,
        "max_abs_error_loocv": {
            "spline": {
                "valor": round(float(np.abs(arr_err_s[idx_peor_s])), 6),
                "minuto": int(_minutos[idx_peor_s]),
                "hora_str": _hora_str(int(_minutos[idx_peor_s])),
            },
            "lagrange": {
                "valor": round(float(np.abs(arr_err_l[idx_peor_l])), 6),
                "minuto": int(_minutos[idx_peor_l]),
                "hora_str": _hora_str(int(_minutos[idx_peor_l])),
            },
        },
        "errores_por_punto": errores_loocv,
    }


def get_resumen() -> dict:
    """
    Devuelve métricas globales del día interpolado.

    Retorna:
        {
          "num_taxis":       int,
          "total_minutos":   int,
          "max_demanda":     {"valor": float, "minuto": int, "hora_str": str},
          "min_demanda":     {"valor": float, "minuto": int, "hora_str": str},
          "max_t_espera":    {"valor": float, "minuto": int, "hora_str": str},
          "demanda_promedio": float,
          "t_espera_promedio": float,
        }
    """
    idx_max = int(np.argmax(_y))
    idx_min = int(np.argmin(_y))

    return {
        "num_taxis":     NUM_TAXIS,
        "total_minutos": int(_x[-1]),
        "max_demanda": {
            "valor":    round(float(_y[idx_max]), 2),
            "minuto":   int(_x[idx_max]),
            "hora_str": _hora_str(int(_x[idx_max])),
        },
        "min_demanda": {
            "valor":    round(float(_y[idx_min]), 2),
            "minuto":   int(_x[idx_min]),
            "hora_str": _hora_str(int(_x[idx_min])),
        },
        "max_t_espera": {
            "valor":    round(float(_y[idx_max]) / NUM_TAXIS, 4),
            "minuto":   int(_x[idx_max]),
            "hora_str": _hora_str(int(_x[idx_max])),
        },
        "demanda_promedio":   round(float(_y.mean()), 4),
        "t_espera_promedio":  round(float(_y.mean()) / NUM_TAXIS, 6),
    }


def get_demanda_en_minuto(minuto: int) -> dict:
    """
    Consulta puntual: devuelve demanda y T_espera para un minuto dado.

    Args:
        minuto: entero entre 0 y 1440.

    Returns:
        {
          "minuto":   int,
          "hora_str": "HH:MM",
          "demanda":  float,
          "t_espera": float,
        }

    Raises:
        ValueError: si el minuto está fuera del rango [0, 1440].
    """
    if not (0 <= minuto <= 1440):
        raise ValueError(f"El minuto debe estar entre 0 y 1440, recibido: {minuto}")

    valor = float(max(0.0, _cs(minuto)))
    return {
        "minuto":   minuto,
        "hora_str": _hora_str(minuto),
        "demanda":  round(valor, 4),
        "t_espera": round(valor / NUM_TAXIS, 6),
    }


# ══════════════════════════════════════════════════════════════════════════
#  Bloque de prueba rápida  (python spline.py)
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json

    print("=== Puntos de control ===")
    for p in get_puntos_control():
        print(f"  {p['hora_str'] if 'hora_str' in p else p['hora']:>5}h  "
              f"→  minuto {p['minuto']:>4}  |  demanda {p['demanda']:>7.2f} rpm")

    print("\n=== Resumen del día ===")
    print(json.dumps(get_resumen(), indent=2, ensure_ascii=False))

    print("\n=== Consulta puntual: minuto 742 (12:22) ===")
    print(json.dumps(get_demanda_en_minuto(742), indent=2))

    print("\n=== Primeros 5 valores del spline completo ===")
    for row in get_spline_completo()[:5]:
        print(f"  {row['hora_str']}  demanda={row['demanda']:>8.4f}  "
              f"T_espera={row['t_espera']:.6f} min")
