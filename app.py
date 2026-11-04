import os
import json
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from db import get_db, init_db, DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_TEMPLATES_DIR = os.path.join(BASE_DIR, "pdf_templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "generated_pdfs")
IMG_DIR = os.path.join(BASE_DIR, "static", "imgs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("DECARRETEO_SECRET", "dev-secret-cambiar-en-produccion")

pdf_env = Environment(loader=FileSystemLoader(PDF_TEMPLATES_DIR))

AEROLINEAS = [
    ("", "— Elegir aerolínea —"),
    ("gol_final.png", "GOL"),
    ("latam_final.png", "LATAM"),
    ("copa_final.png", "Copa Airlines"),
    ("avianca_final.png", "Avianca"),
    ("ux_final.png", "Air Europa"),
    ("arajet_final.png", "Arajet"),
    ("lufthansa_final.png", "Lufthansa"),
    ("sky_final.png", "Sky Airline"),
    ("klm_final.png", "KLM"),
    ("chinaeastern_final.png", "China Eastern"),
    ("delta_final.png", "Delta"),
    ("emirates_final.png", "Emirates"),
    ("ethiopian_final.png", "Ethiopian Airlines"),
    ("aerolineasargentinas_final.png", "Aerolíneas Argentinas"),
    ("turkish_final.png", "Turkish Airlines"),
    ("airfrance_final.png", "Air France"),
    ("jetsmart_final.png", "JetSMART"),
]

CONDICIONES_DEFAULT = [
    "Los precios y la disponibilidad están sujetos a cambios hasta que se confirme la reserva.",
    "Los asientos se asignarán automáticamente según las políticas de la aerolínea.",
    "La validez de esta cotización es hasta el día y horario indicado.",
    "Para confirmar la reserva se requiere el pago de la seña; el saldo debe abonarse según lo indicado.",
    "Las políticas de cancelación y reembolso están sujetas a las reglas de la aerolínea.",
    "La documentación necesaria para realizar el viaje es responsabilidad del pasajero.",
    "Recomendamos verificar la vacuna de fiebre amarilla para su viaje, es requisito para muchos destinos.",
]

NOTA_OPCIONES = {
    "ninguna": "",
    "no_asistencia": "esta tarifa no incluye asistencia al viajero, la cual consideramos importante — puede consultarla con nosotros.",
    "no_checkinout": "esta tarifa no incluye <i>early check-in</i> ni <i>late check-out</i>.",
    "ambas": "esta tarifa no incluye asistencia al viajero ni <i>early check-in</i>/<i>late check-out</i>.",
}

DEFAULT_ADVISOR = {
    "nombre": "Francisco Carreño",
    "telefono": "+54 9 3518 72-5838",
    "email": "",
}


# ---------------------------------------------------------------- auth utils

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return user


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not u["is_admin"]:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_user():
    return {"user": current_user()}


# -------------------------------------------------------------------- seed

def seed_admin():
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", ("fran166carre@gmail.com",)).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, phone, is_admin, can_view_all) VALUES (?,?,?,?,1,1)",
            ("Francisco Carreño", "fran166carre@gmail.com", generate_password_hash("decarreteo2026"), "+54 9 3518 72-5838"),
        )
        conn.commit()
    conn.close()


# ------------------------------------------------------------------ routes

@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"¡Bienvenido/a, {user['name']}!", "success")
            nxt = request.args.get("next") or url_for("dashboard")
            return redirect(nxt)
        flash("Email o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        if not name or not email or not password:
            flash("Completá nombre, email y contraseña.", "error")
            return render_template("registro.html")
        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("Ya existe una cuenta con ese email.", "error")
            return render_template("registro.html")
        conn.execute(
            "INSERT INTO users (name, email, password_hash, phone, is_admin, can_view_all) VALUES (?,?,?,?,0,0)",
            (name, email, generate_password_hash(password), phone),
        )
        conn.commit()
        conn.close()
        flash("Cuenta creada. Ya podés iniciar sesión.", "success")
        return redirect(url_for("login"))
    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ------------------------------------------------------------ nueva cotización

@app.route("/nueva")
@login_required
def nueva_tipo():
    return render_template("nueva_tipo.html")


@app.route("/nueva/<tipo>", methods=["GET", "POST"])
@login_required
def nueva_formulario(tipo):
    if tipo not in ("hotel_unico", "multi_hotel", "itinerario"):
        abort(404)

    if request.method == "POST":
        errores = []
        data = parse_form(tipo, request.form, errores)

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template(
                f"form_{tipo}.html",
                aerolineas=AEROLINEAS,
                condiciones_default="\n".join(CONDICIONES_DEFAULT),
                default_advisor=DEFAULT_ADVISOR,
                form=request.form,
            )

        # Generar PDF
        html_out = pdf_env.get_template(f"{tipo}.html").render(**data)
        img_base_fs = "file://" + IMG_DIR
        html_out = html_out  # img_base already injected into data as file:// path

        filename = f"{tipo}_{uuid.uuid4().hex[:8]}.pdf"
        out_path = os.path.join(OUTPUT_DIR, filename)
        HTML(string=html_out, base_url=BASE_DIR).write_pdf(out_path)

        conn = get_db()
        conn.execute(
            "INSERT INTO quotes (user_id, tipo, destino, cliente, pdf_filename, form_data) VALUES (?,?,?,?,?,?)",
            (
                current_user()["id"],
                tipo,
                data.get("destino_titulo", ""),
                request.form.get("cliente", ""),
                filename,
                json.dumps({k: request.form.getlist(k) if len(request.form.getlist(k)) > 1 else request.form.get(k) for k in request.form}),
            ),
        )
        conn.commit()
        conn.close()

        flash("¡Cotización generada con éxito!", "success")
        return redirect(url_for("descargar", filename=filename))

    return render_template(
        f"form_{tipo}.html",
        aerolineas=AEROLINEAS,
        condiciones_default="\n".join(CONDICIONES_DEFAULT),
        default_advisor=DEFAULT_ADVISOR,
        form={},
    )


def parse_form(tipo, form, errores):
    """Valida y arma el dict de datos para el template PDF. Agrega mensajes a `errores` en vez de inventar datos."""
    data = {"img_base": "file://" + IMG_DIR}

    def req(field, label):
        v = form.get(field, "").strip()
        if not v:
            errores.append(f"Falta completar: {label}.")
        return v

    tipo_cot = form.get("tipo_cotizacion", "cotizacion")
    eyebrow_map = {
        "cotizacion": "Cotización de viaje",
        "salida_grupal": "Salida Grupal",
        "itinerario": "Itinerario de viaje",
    }
    destino = req("destino", "Destino")
    mes_anio = req("mes_anio", "Mes y año del viaje")
    data["eyebrow"] = f"{eyebrow_map.get(tipo_cot, 'Cotización de viaje')} &middot; {mes_anio}"
    data["destino_titulo"] = destino
    data["subtitulo"] = form.get("subtitulo", "").strip()
    data["origen"] = req("origen", "Origen (ciudad de salida)")
    data["fechas"] = req("fechas", "Fechas del viaje")
    data["duracion"] = req("duracion", "Duración total")
    data["pie_pagina"] = destino or "Cotización"

    # Servicios incluidos
    servicios_raw = form.get("servicios", "")
    servicios = [s.strip() for s in servicios_raw.splitlines() if s.strip()]
    if not servicios:
        errores.append("Agregá al menos un servicio incluido.")
    data["servicios"] = servicios

    # Vuelos
    sin_vuelos = form.get("sin_vuelos") == "on"
    vuelos = []
    if not sin_vuelos:
        n_tramos = int(form.get("vuelos_count", "0") or 0)
        if n_tramos == 0:
            errores.append("Agregá al menos un tramo de vuelo, o marcá 'Todavía no tengo los datos del vuelo'.")
        for i in range(n_tramos):
            p = f"vuelo_{i}_"
            tag = form.get(p + "tag", "").strip()
            aerolinea = form.get(p + "aerolinea_nombre", "").strip()
            logo = form.get(p + "aerolinea", "")
            numero = form.get(p + "numero", "").strip()
            fecha_o = form.get(p + "fecha_origen", "").strip()
            hora_o = form.get(p + "hora_origen", "").strip()
            iata_o = form.get(p + "iata_origen", "").strip().upper()
            aero_o = form.get(p + "aeropuerto_origen", "").strip()
            fecha_d = form.get(p + "fecha_destino", "").strip()
            hora_d = form.get(p + "hora_destino", "").strip()
            iata_d = form.get(p + "iata_destino", "").strip().upper()
            aero_d = form.get(p + "aeropuerto_destino", "").strip()
            directo = form.get(p + "directo", "on") == "on"
            duracion_v = form.get(p + "duracion", "").strip()
            espera = form.get(p + "espera", "").strip()
            aeropuerto_escala = form.get(p + "aeropuerto_escala", "").strip()

            campos_tramo = {
                "Tramo/etiqueta": tag, "Aerolínea": aerolinea, "N° de vuelo": numero,
                "Fecha origen": fecha_o, "Hora origen": hora_o, "Código IATA origen": iata_o,
                "Aeropuerto origen": aero_o, "Fecha destino": fecha_d, "Hora destino": hora_d,
                "Código IATA destino": iata_d, "Aeropuerto destino": aero_d, "Duración": duracion_v,
            }
            faltantes = [k for k, v in campos_tramo.items() if not v]
            if faltantes:
                errores.append(f"Vuelo tramo {i+1}: faltan los campos: {', '.join(faltantes)}.")

            vuelos.append({
                "tag": tag, "aerolinea": aerolinea, "logo": logo, "numero_vuelo": numero,
                "fecha_origen": fecha_o, "hora_origen": hora_o, "iata_origen": iata_o, "aeropuerto_origen": aero_o,
                "fecha_destino": fecha_d, "hora_destino": hora_d, "iata_destino": iata_d, "aeropuerto_destino": aero_d,
                "directo": directo, "duracion": duracion_v, "duracion_total": duracion_v,
                "espera": espera, "aeropuerto_escala": aeropuerto_escala,
            })
    data["vuelos"] = vuelos

    # Nota importante
    nota_opcion = form.get("nota_opcion", "")
    if nota_opcion not in NOTA_OPCIONES:
        errores.append("Elegí una opción para la nota de asistencia / early-late checkout (no se puede dejar sin definir).")
        nota_opcion = "ninguna"
    data["nota_texto"] = NOTA_OPCIONES[nota_opcion]

    # Precios / condiciones / pago / asesor — delegado por tipo
    if tipo == "hotel_unico":
        data.update(parse_hotel_unico(form, errores))
    elif tipo == "multi_hotel":
        data.update(parse_multi_hotel(form, errores))
    elif tipo == "itinerario":
        data.update(parse_itinerario(form, errores))

    # Condiciones
    cond_raw = form.get("condiciones", "")
    condiciones = [c.strip() for c in cond_raw.splitlines() if c.strip()]
    if not condiciones:
        errores.append("Las condiciones no pueden quedar vacías.")
    data["condiciones"] = condiciones

    # Forma de pago
    omitir_pago = form.get("omitir_pago") == "on"
    data["omitir_pago"] = omitir_pago
    if not omitir_pago:
        data["sena"] = req("sena", "Seña de reserva (o marcá 'omitir forma de pago')")
        data["saldo"] = req("saldo", "Condición de saldo (o marcá 'omitir forma de pago')")
        data["medios_pago"] = req("medios_pago", "Medios de pago (o marcá 'omitir forma de pago')")
    else:
        data["sena"] = data["saldo"] = data["medios_pago"] = ""
    data["validez"] = form.get("validez", "").strip()

    # Asesor
    asesor_nombre = req("asesor_nombre", "Nombre del asesor")
    asesor_telefono = req("asesor_telefono", "Teléfono del asesor")
    data["asesor_nombre"] = asesor_nombre
    data["asesor_telefono"] = asesor_telefono
    data["asesor_email"] = form.get("asesor_email", "").strip()
    iniciales = "".join([p[0].upper() for p in asesor_nombre.split()[:2]]) if asesor_nombre else "FC"
    data["asesor_iniciales"] = iniciales

    return data


def parse_hotel_unico(form, errores):
    d = {}
    d["hotel"] = {
        "ciudad": form.get("hotel_ciudad", "").strip(),
        "nombre": form.get("hotel_nombre", "").strip(),
        "noches": form.get("hotel_noches", "").strip(),
        "regimen": form.get("hotel_regimen", "").strip(),
    }
    for campo, label in [("ciudad", "Ciudad del hotel"), ("nombre", "Nombre del hotel"), ("noches", "Noches")]:
        if not d["hotel"][campo]:
            errores.append(f"Hotel: falta {label}.")

    n_precios = int(form.get("precios_count", "0") or 0)
    precios = []
    for i in range(n_precios):
        label = form.get(f"precio_{i}_label", "").strip()
        monto = form.get(f"precio_{i}_monto", "").strip()
        if not label or not monto:
            errores.append(f"Precio #{i+1}: completá la etiqueta y el monto.")
        precios.append({"label": label, "monto": monto})
    if not precios:
        errores.append("Agregá al menos una tarifa.")
    d["precios"] = precios
    d["precio_titulo"] = "Tarifas"
    return d


def parse_multi_hotel(form, errores):
    d = {}
    n_hoteles = int(form.get("hoteles_count", "0") or 0)
    hoteles = []
    for i in range(n_hoteles):
        nombre = form.get(f"hotel_{i}_nombre", "").strip()
        regimen = form.get(f"hotel_{i}_regimen", "").strip()
        noches = form.get(f"hotel_{i}_noches", "").strip()
        precio = form.get(f"hotel_{i}_precio", "").strip()
        faltan = [n for n, v in [("nombre", nombre), ("régimen", regimen), ("noches", noches), ("precio", precio)] if not v]
        if faltan:
            errores.append(f"Hotel #{i+1}: faltan {', '.join(faltan)}.")
        hoteles.append({"nombre": nombre, "regimen": regimen, "noches": noches, "precio": precio})
    if len(hoteles) < 2:
        errores.append("Multi-hotel necesita al menos 2 opciones de hotel.")
    try:
        hoteles.sort(key=lambda h: float(h["precio"].replace(",", "")) if h["precio"] else 0)
    except ValueError:
        pass
    d["hoteles"] = hoteles
    d["hotel_nota"] = form.get("hotel_nota", "").strip()
    return d


def parse_itinerario(form, errores):
    d = {}
    n_dias = int(form.get("dias_count", "0") or 0)
    dias = []
    for i in range(n_dias):
        numero = form.get(f"dia_{i}_numero", "").strip()
        fecha_label = form.get(f"dia_{i}_fecha", "").strip()
        ciudad = form.get(f"dia_{i}_ciudad", "").strip()
        intro = form.get(f"dia_{i}_intro", "").strip()
        tip = form.get(f"dia_{i}_tip", "").strip()
        actividades_raw = form.get(f"dia_{i}_actividades", "")
        actividades = [a.strip() for a in actividades_raw.splitlines() if a.strip()]
        if not numero or not ciudad:
            errores.append(f"Día #{i+1}: falta número de día o ciudad.")
        dias.append({"numero": numero, "fecha_label": fecha_label, "ciudad": ciudad, "intro": intro, "tip": tip, "actividades": actividades})
    if not dias:
        errores.append("Agregá al menos un día al itinerario.")
    d["dias"] = dias

    hoteles_modo = form.get("hoteles_modo", "simple")
    d["hoteles_modo"] = hoteles_modo
    if hoteles_modo == "simple":
        n = int(form.get("hoteles_simple_count", "0") or 0)
        hoteles_simple = []
        for i in range(n):
            ciudad = form.get(f"hs_{i}_ciudad", "").strip()
            nombre = form.get(f"hs_{i}_nombre", "").strip()
            if not ciudad or not nombre:
                errores.append(f"Hotel por ciudad #{i+1}: falta ciudad o nombre.")
            hoteles_simple.append({"ciudad": ciudad, "nombre": nombre})
        if not hoteles_simple:
            errores.append("Agregá al menos un hotel por ciudad.")
        d["hoteles_simple"] = hoteles_simple
        d["hoteles_con_precio"] = []
    else:
        n = int(form.get("hoteles_precio_count", "0") or 0)
        hoteles_cp = []
        for i in range(n):
            nombre = form.get(f"hp_{i}_nombre", "").strip()
            regimen = form.get(f"hp_{i}_regimen", "").strip()
            noches = form.get(f"hp_{i}_noches", "").strip()
            precio = form.get(f"hp_{i}_precio", "").strip()
            if not nombre or not precio:
                errores.append(f"Hotel con precio #{i+1}: falta nombre o precio.")
            hoteles_cp.append({"nombre": nombre, "regimen": regimen, "noches": noches, "precio": precio})
        if not hoteles_cp:
            errores.append("Agregá al menos una opción de hotel con precio.")
        try:
            hoteles_cp.sort(key=lambda h: float(h["precio"].replace(",", "")) if h["precio"] else 0)
        except ValueError:
            pass
        d["hoteles_con_precio"] = hoteles_cp
        d["hoteles_simple"] = []

    incluye_raw = form.get("incluye", "")
    no_incluye_raw = form.get("no_incluye", "")
    d["incluye"] = [x.strip() for x in incluye_raw.splitlines() if x.strip()]
    d["no_incluye"] = [x.strip() for x in no_incluye_raw.splitlines() if x.strip()]

    hay_precio = form.get("hay_precio") == "on"
    precios = []
    if hay_precio:
        n_precios = int(form.get("precios_count", "0") or 0)
        for i in range(n_precios):
            label = form.get(f"precio_{i}_label", "").strip()
            monto = form.get(f"precio_{i}_monto", "").strip()
            if not label or not monto:
                errores.append(f"Precio #{i+1}: completá etiqueta y monto.")
            precios.append({"label": label, "monto": monto})
        if not precios:
            errores.append("Marcaste que hay tarifa confirmada: agregá al menos un precio.")
    d["precios"] = precios
    d["precio_titulo"] = "Tarifa" if precios else ""
    return d


@app.route("/descargar/<filename>")
@login_required
def descargar(filename):
    conn = get_db()
    q = conn.execute("SELECT * FROM quotes WHERE pdf_filename = ?", (filename,)).fetchone()
    conn.close()
    if not q:
        abort(404)
    u = current_user()
    if q["user_id"] != u["id"] and not (u["is_admin"] or u["can_view_all"]):
        abort(403)
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=False, download_name=f"cotizacion_{q['destino']}.pdf")


@app.route("/historial")
@login_required
def historial():
    u = current_user()
    conn = get_db()
    if u["is_admin"] or u["can_view_all"]:
        quotes = conn.execute(
            "SELECT q.*, u.name as user_name FROM quotes q JOIN users u ON u.id = q.user_id ORDER BY q.created_at DESC"
        ).fetchall()
    else:
        quotes = conn.execute(
            "SELECT q.*, u.name as user_name FROM quotes q JOIN users u ON u.id = q.user_id WHERE q.user_id = ? ORDER BY q.created_at DESC",
            (u["id"],),
        ).fetchall()
    conn.close()
    return render_template("historial.html", quotes=quotes, ve_todas=bool(u["is_admin"] or u["can_view_all"]))


# ------------------------------------------------------------ admin: permisos

@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    conn = get_db()
    usuarios = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
    conn.close()
    return render_template("admin_usuarios.html", usuarios=usuarios)


@app.route("/admin/usuarios/<int:user_id>/toggle_ver_todas", methods=["POST"])
@admin_required
def admin_toggle_ver_todas(user_id):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not u:
        conn.close()
        abort(404)
    nuevo = 0 if u["can_view_all"] else 1
    conn.execute("UPDATE users SET can_view_all = ? WHERE id = ?", (nuevo, user_id))
    conn.commit()
    conn.close()
    flash(f"Permiso 've todas' {'otorgado a' if nuevo else 'quitado a'} {u['name']}.", "success")
    return redirect(url_for("admin_usuarios"))


# Se ejecuta siempre al importar el módulo (tanto en `python app.py` como bajo
# gunicorn en producción), para que la base de datos y el admin por defecto
# existan sin depender de un paso manual de deploy.
init_db()
seed_admin()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
