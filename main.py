"""
main.py — TaxiDemand Flask App
==============================
Rutas:
  GET  /              → landing page
  GET  /login         → formulario de login
  POST /login         → autenticación
  GET  /logout        → cerrar sesión
  GET  /dashboard     → panel principal (requiere login)
  GET  /api/spline    → JSON con los 1441 puntos del spline
  GET  /api/consulta  → JSON consulta puntual ?minuto=N
"""

from pathlib import Path

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify, flash, Response
)
from spline import (
    get_puntos_control,
    get_spline_completo,
    get_lagrange_completo,
    get_resumen,
    get_demanda_en_minuto,
    get_comparativa_modelos,
    get_arima_forecast,
    set_datos_raw,
    generar_recursos_visuales,
)

app = Flask(__name__)
app.secret_key = "taxi-demand-secret-2025"   # cambiar en producción
_GIF_PATH = Path(__file__).resolve().parent / "static" / "img" / "animacion_spline.gif"
_PNG_PATH = Path(__file__).resolve().parent / "static" / "img" / "grafico_spline_cubico.png"

# ── Credenciales demo (en producción usar BD + hash) ──────────
USUARIOS = {
    "admin": "1234",
}

# ── Datos precalculados al arrancar (no recalcular en cada req) 
_PUNTOS_CONTROL = get_puntos_control()
_SPLINE_DATA    = get_spline_completo()
_LAGRANGE_DATA  = get_lagrange_completo()
_RESUMEN        = get_resumen()
_COMPARATIVA    = get_comparativa_modelos()
generar_recursos_visuales()


def _asset_version(path: Path) -> int:
    try:
        return int(path.stat().st_mtime_ns)
    except FileNotFoundError:
        return 0


# ══════════════════════════════════════════════════════════════
#  Decorador de protección de ruta
# ══════════════════════════════════════════════════════════════
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════
#  RUTAS DE PÁGINAS
# ══════════════════════════════════════════════════════════════

@app.route("/")
def landing():
    return render_template("landing.html", resumen=_RESUMEN)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        usuario  = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if USUARIOS.get(usuario) == password:
            session["logged_in"] = True
            session["usuario"]   = usuario
            return redirect(url_for("dashboard"))
        else:
            error = "Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        resumen             = _RESUMEN,
        puntos_control      = _PUNTOS_CONTROL,
        spline_data         = _SPLINE_DATA,
        lagrange_data       = _LAGRANGE_DATA,
        comparativa_modelos = _COMPARATIVA,
        spline_png_version  = _asset_version(_PNG_PATH),
        spline_gif_version  = _asset_version(_GIF_PATH),
    )


# ══════════════════════════════════════════════════════════════
#  CARGA DE CSV POR EL USUARIO
# ══════════════════════════════════════════════════════════════

MAX_CSV_BYTES = 256 * 1024  # 256 KB

@app.route("/upload-csv", methods=["POST"])
@login_required
def upload_csv():
    global _PUNTOS_CONTROL, _SPLINE_DATA, _LAGRANGE_DATA, _RESUMEN, _COMPARATIVA

    archivo = request.files.get("csv_file")
    if not archivo or archivo.filename == "":
        flash("Selecciona un archivo CSV antes de enviar.", "error")
        return redirect(url_for("dashboard"))

    if not archivo.filename.lower().endswith(".csv"):
        flash("Solo se aceptan archivos con extensión .csv", "error")
        return redirect(url_for("dashboard"))

    raw = archivo.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        flash("El archivo supera el tamaño máximo permitido (256 KB).", "error")
        return redirect(url_for("dashboard"))

    try:
        texto = raw.decode("utf-8-sig")  # utf-8-sig elimina BOM de Excel
    except UnicodeDecodeError:
        flash("El archivo no está en formato UTF-8.", "error")
        return redirect(url_for("dashboard"))

    datos = []
    errores_linea = []
    for num, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.replace(";", ",").split(",")
        if len(partes) < 2:
            continue
        try:
            hora    = float(partes[0].strip())
            demanda = float(partes[1].strip())
        except ValueError:
            if num == 1:
                continue  # saltar encabezado
            errores_linea.append(num)
            continue

        if not (0.0 <= hora <= 24.0):
            flash(f"Línea {num}: la hora {hora} está fuera del rango [0, 24].", "error")
            return redirect(url_for("dashboard"))
        if demanda < 0:
            flash(f"Línea {num}: la demanda no puede ser negativa.", "error")
            return redirect(url_for("dashboard"))

        datos.append((hora, demanda))

    if errores_linea:
        flash(f"Se ignoraron {len(errores_linea)} líneas con valores no numéricos.", "warning")

    if len(datos) < 4:
        flash("El CSV debe tener al menos 4 puntos válidos (hora, demanda).", "error")
        return redirect(url_for("dashboard"))

    # Verificar horas únicas (CubicSpline las requiere)
    horas_unicas = {h for h, _ in datos}
    if len(horas_unicas) != len(datos):
        flash("El CSV contiene horas duplicadas. Cada hora debe aparecer solo una vez.", "error")
        return redirect(url_for("dashboard"))

    try:
        set_datos_raw(datos)
    except Exception as e:
        flash(f"Error al recalcular los modelos: {e}", "error")
        return redirect(url_for("dashboard"))

    _PUNTOS_CONTROL = get_puntos_control()
    _SPLINE_DATA    = get_spline_completo()
    _LAGRANGE_DATA  = get_lagrange_completo()
    _RESUMEN        = get_resumen()
    _COMPARATIVA    = get_comparativa_modelos()

    flash(f"Datos actualizados correctamente ({len(datos)} puntos de control cargados).", "success")
    return redirect(url_for("dashboard"))


@app.route("/csv-template")
@login_required
def csv_template():
    """Descarga el CSV de plantilla con los datos actuales."""
    lineas = ["hora,demanda"]
    for p in _PUNTOS_CONTROL:
        lineas.append(f"{p['hora']},{p['demanda']}")
    contenido = "\n".join(lineas)
    return Response(
        contenido,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=datos_demanda.csv"},
    )


# ══════════════════════════════════════════════════════════════
#  API JSON
# ══════════════════════════════════════════════════════════════

@app.route("/api/spline")
@login_required
def api_spline():
    """Devuelve los 1441 puntos del spline como JSON."""
    return jsonify({
        "resumen": _RESUMEN,
        "comparativa_modelos": _COMPARATIVA,
        "datos":   _SPLINE_DATA,
    })


@app.route("/api/consulta")
@login_required
def api_consulta():
    """
    Consulta puntual por minuto.
    Query param: ?minuto=<int>  (0 – 1440)
    """
    try:
        minuto = int(request.args.get("minuto", 0))
        return jsonify(get_demanda_en_minuto(minuto))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/arima")
@login_required
def api_arima():
    """
    Predicción ARIMA(2,1,1) + Spline para los próximos 30 minutos.
    Query param: ?minuto=<int>  (120 – 1440)
    """
    try:
        minuto = int(request.args.get("minuto", 720))
        minuto = max(120, min(1440, minuto))
        return jsonify(get_arima_forecast(minuto))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ══════════════════════════════════════════════════════════════
#  ARRANQUE
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, port=5000)
