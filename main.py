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

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify
)
from spline import (
    get_puntos_control,
    get_spline_completo,
    get_lagrange_completo,
    get_resumen,
    get_demanda_en_minuto,
    get_comparativa_modelos,
)

app = Flask(__name__)
app.secret_key = "taxi-demand-secret-2025"   # cambiar en producción

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


# ══════════════════════════════════════════════════════════════
#  ARRANQUE
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, port=5000)
