"""
spline.py — Lógica de interpolación de Splines Cúbicos
=======================================================
Módulo independiente de Flask. Contiene:
  - Datos originales de demanda (horas → minutos)
  - Interpolación con CubicSpline (1440 valores)
  - Funciones de acceso para la app Flask
"""

import numpy as np
from scipy.interpolate import CubicSpline, BarycentricInterpolator

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

# Datos activos (pueden sobreescribirse con set_datos_raw)
_datos_actuales = list(DATOS_RAW)

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
        for h, d in _datos_actuales
    ]


def get_spline_completo() -> list[dict]:
    """
    Devuelve los 1441 puntos interpolados (minuto 0 … 1440).

    Cada elemento:
        {
          "minuto":   int,    # 0 … 1440
          "hora_str": "HH:MM",
          "demanda":  float,  # solicitudes/minuto  (≥ 0)
        }
    """
    resultado = []
    for x, y in zip(_x.tolist(), _y.tolist()):
        resultado.append({
            "minuto":   int(x),
            "hora_str": _hora_str(int(x)),
            "demanda":  round(float(y), 4),
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
        }
    """
    resultado = []
    for x, y in zip(_x.tolist(), _y_lagrange.tolist()):
        resultado.append({
            "minuto":   int(x),
            "hora_str": _hora_str(int(x)),
            "demanda":  round(float(y), 4),
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
          "total_minutos":   int,
          "max_demanda":     {"valor": float, "minuto": int, "hora_str": str},
          "min_demanda":     {"valor": float, "minuto": int, "hora_str": str},
          "demanda_promedio": float,
        }
    """
    idx_max = int(np.argmax(_y))
    idx_min = int(np.argmin(_y))

    return {
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
        "demanda_promedio":   round(float(_y.mean()), 4),
    }


def get_demanda_en_minuto(minuto: int) -> dict:
    """
    Consulta puntual: devuelve demanda para un minuto dado.

    Args:
        minuto: entero entre 0 y 1440.

    Returns:
        {
          "minuto":   int,
          "hora_str": "HH:MM",
          "demanda":  float,
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
    }


# ── Umbral de alerta para el modelo ARIMA ────────────────────────────────
ALERTA_UMBRAL = 150.0   # solicitudes/minuto


def get_arima_forecast(minuto_actual: int,
                       horizonte: int = 30,
                       ventana_hist: int = 120) -> dict:
    """
    Predicción híbrida Spline + ARIMA(2,1,1) para los próximos `horizonte` minutos.

    Combina:
      - Spline cúbico   → captura la tendencia macro del día
      - AR(2) + d=1     → modela la autocorrelación del ruido en primeras diferencias
      - MA(1)           → corrige el error del paso anterior

    El ajuste se hace sobre residuos sintéticos (spline + ruido gaussiano reproducible)
    que simulan datos históricos reales con variabilidad estocástica.
    Genera alertas cuando la demanda pronosticada supera ALERTA_UMBRAL.

    Returns:
        {
          "minuto_actual": int,
          "hora_actual":   str,
          "horizonte":     int,
          "umbral_alerta": float,
          "parametros":    {"phi1": float, "phi2": float, "theta": float, "orden": str},
          "forecast":      [{"minuto": int, "hora_str": str, "demanda": float,
                             "spline": float, "alerta": bool}, ...],
          "alertas":       [{"minuto": int, "hora_str": str, "demanda_pred": float,
                             "nivel": "alta"|"critica"}, ...],
          "historia":      [{"minuto": int, "hora_str": str, "demanda": float,
                             "spline": float}, ...],
        }
    """
    minuto_actual = int(np.clip(minuto_actual, ventana_hist, 1440))
    inicio = max(0, minuto_actual - ventana_hist)

    hist_x      = np.arange(inicio, minuto_actual, dtype=float)
    spline_hist = np.clip(_cs(hist_x), 0.0, None)

    # Datos históricos simulados = spline + ruido gaussiano (σ ≈ 4 % + offset 0.5)
    # Seed determinista por minuto → reproducible, pero varía con la hora elegida
    rng   = np.random.default_rng(seed=minuto_actual)
    ruido = rng.normal(0.0, np.maximum(spline_hist * 0.04, 0.5))
    hist_y = np.clip(spline_hist + ruido, 0.0, None)

    # Residuos respecto al spline (la tendencia ya está capturada)
    residuos = hist_y - spline_hist

    # Primera diferencia de residuos (d = 1)
    d_res = np.diff(residuos)
    n     = len(d_res)

    # ── AR(2) por OLS ──────────────────────────────────────────────────────
    phi1, phi2 = 0.0, 0.0
    if n >= 4:
        # Matriz de diseño: [d_{t-1}, d_{t-2}]
        X_ar = np.column_stack([d_res[1:-1], d_res[:-2]])
        y_ar = d_res[2:]
        XtX  = X_ar.T @ X_ar + np.eye(2) * 1e-6   # regularización de Tikhonov
        Xty  = X_ar.T @ y_ar
        try:
            coeffs = np.linalg.solve(XtX, Xty)
            phi1, phi2 = float(coeffs[0]), float(coeffs[1])
            # Restringir radio espectral para garantizar estacionariedad
            norm = np.sqrt(phi1 ** 2 + phi2 ** 2)
            if norm > 0.97:
                phi1, phi2 = phi1 / norm * 0.97, phi2 / norm * 0.97
        except np.linalg.LinAlgError:
            phi1, phi2 = 0.0, 0.0

    # ── MA(1) por OLS sobre los residuos del AR ────────────────────────────
    theta    = 0.0
    last_eps = 0.0
    if n >= 4:
        fitted_ar = phi1 * d_res[1:-1] + phi2 * d_res[:-2]
        eps_ar    = d_res[2:] - fitted_ar
        if len(eps_ar) >= 2:
            num   = float(np.dot(eps_ar[:-1], eps_ar[1:]))
            den   = float(np.dot(eps_ar[:-1], eps_ar[:-1])) + 1e-10
            theta = float(np.clip(num / den, -0.9, 0.9))
            last_eps = float(eps_ar[-1])

    # ── Pronóstico h pasos hacia adelante ─────────────────────────────────
    last_res = float(residuos[-1])
    d_buf    = list(d_res[-2:]) if n >= 2 else [0.0, 0.0]
    eps_fut  = last_eps

    forecast = []
    alertas  = []

    for h in range(1, horizonte + 1):
        min_fut = minuto_actual + h
        if min_fut > 1440:
            break

        d1     = d_buf[-1] if len(d_buf) >= 1 else 0.0
        d2     = d_buf[-2] if len(d_buf) >= 2 else 0.0
        d_pred = phi1 * d1 + phi2 * d2 + theta * eps_fut

        last_res = last_res + d_pred
        sp_fut   = float(max(0.0, _cs(float(min_fut))))
        dem_pred = round(float(max(0.0, sp_fut + last_res)), 2)
        alerta   = bool(dem_pred > ALERTA_UMBRAL)

        forecast.append({
            "minuto":   min_fut,
            "hora_str": _hora_str(min_fut),
            "demanda":  dem_pred,
            "spline":   round(sp_fut, 2),
            "alerta":   alerta,
        })
        if alerta:
            alertas.append({
                "minuto":       min_fut,
                "hora_str":     _hora_str(min_fut),
                "demanda_pred": dem_pred,
                "nivel":        "critica" if dem_pred > ALERTA_UMBRAL * 1.2 else "alta",
            })

        d_buf.append(d_pred)
        eps_fut = 0.0   # E[ε_{t+h}] = 0 para h > 1

    # Historia submuestreada para el gráfico (máx 60 puntos)
    paso = max(1, len(hist_x) // 60)
    historia = [
        {
            "minuto":   int(hist_x[i]),
            "hora_str": _hora_str(int(hist_x[i])),
            "demanda":  round(float(hist_y[i]), 2),
            "spline":   round(float(spline_hist[i]), 2),
        }
        for i in range(0, len(hist_x), paso)
    ]

    return {
        "minuto_actual": minuto_actual,
        "hora_actual":   _hora_str(minuto_actual),
        "horizonte":     horizonte,
        "umbral_alerta": ALERTA_UMBRAL,
        "parametros": {
            "phi1":  round(phi1, 6),
            "phi2":  round(phi2, 6),
            "theta": round(theta, 6),
            "orden": "ARIMA(2,1,1)",
        },
        "forecast": forecast,
        "alertas":  alertas,
        "historia": historia,
    }


def set_datos_raw(nuevos_datos: list[tuple[float, float]]) -> None:
    """
    Reemplaza los datos de demanda y recalcula todos los modelos.

    Args:
        nuevos_datos: lista de tuplas (hora_decimal, demanda).
                      Debe tener al menos 4 puntos.
                      Las horas deben ser únicas y en rango [0, 24].
    """
    global _datos_actuales, _horas, _demanda, _minutos
    global _cs, _lagrange, _x, _y, _y_lagrange

    datos = sorted(nuevos_datos, key=lambda t: t[0])  # ordenar por hora
    _datos_actuales = list(datos)

    _horas   = np.array([d[0] for d in _datos_actuales])
    _demanda = np.array([d[1] for d in _datos_actuales])
    _minutos = _horas * 60

    max_min = int(round(float(_minutos[-1])))
    _x = np.arange(0, max_min + 1)

    _cs       = CubicSpline(_minutos, _demanda)
    _lagrange = BarycentricInterpolator(_minutos, _demanda)

    _y         = np.clip(_cs(_x), 0, None)
    _y_lagrange = np.clip(_lagrange(_x), 0, None)


# ══════════════════════════════════════════════════════════════════════════
#  Bloque de prueba rápida  (python spline.py)
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json

    print("=== Puntos de control ===")
    for p in get_puntos_control():
        print(f"  {p['hora_str'] if 'hora_str' in p else p['hora']:>5}h  "
              f"→  minuto {p['minuto']:>4}  |  demanda {p['demanda']:>7.2f} solicitudes")

    print("\n=== Resumen del día ===")
    print(json.dumps(get_resumen(), indent=2, ensure_ascii=False))

    print("\n=== Consulta puntual: minuto 742 (12:22) ===")
    print(json.dumps(get_demanda_en_minuto(742), indent=2))

    print("\n=== Primeros 5 valores del spline completo ===")
    for row in get_spline_completo()[:5]:
        print(f"  {row['hora_str']}  demanda={row['demanda']:>8.4f}")
