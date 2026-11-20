import os
from datetime import date
from io import BytesIO

from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook

import db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-cambiar")


def conexion():
    if "db" not in g:
        g.db = db.conectar()
    return g.db


@app.teardown_appcontext
def cerrar_conexion(_exc):
    conn = g.pop("db", None)
    if conn:
        conn.close()


@app.context_processor
def datos_globales():
    return dict(locales=db.listar_locales(conexion()), hoy=date.today().isoformat())


def local_param():
    valor = request.args.get("local", "")
    return int(valor) if valor.isdigit() else None


def producto_or_404(producto_id):
    producto = db.obtener_producto(conexion(), producto_id)
    if not producto:
        abort(404)
    return producto


@app.get("/")
def inicio():
    return redirect(url_for("listado_productos"))


@app.get("/productos")
def listado_productos():
    conn = conexion()
    local = local_param()
    q = request.args.get("q", "").strip()
    return render_template(
        "productos.html",
        productos=db.listar_productos(conn, local, q or None),
        alertas=len(db.listar_alertas(conn, local)),
        local=local,
        q=q,
    )


@app.route("/productos/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    conn = conexion()
    error = None
    if request.method == "POST":
        try:
            db.crear_producto(
                conn,
                request.form.get("nombre"),
                request.form.get("categoria"),
                request.form.get("local_id"),
                request.form.get("stock"),
                request.form.get("stock_minimo"),
            )
            flash("Producto registrado.", "ok")
            return redirect(url_for("listado_productos", local=request.form.get("local_id")))
        except ValueError as e:
            error = str(e)
    v = request.form if request.method == "POST" else {}
    return render_template("producto_form.html", titulo="Nuevo producto", v=v, error=error, editar=False)


@app.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
def editar_producto(producto_id):
    conn = conexion()
    producto = producto_or_404(producto_id)
    error = None
    if request.method == "POST":
        try:
            db.editar_producto(
                conn,
                producto_id,
                request.form.get("nombre"),
                request.form.get("categoria"),
                request.form.get("stock_minimo"),
            )
            flash("Producto actualizado.", "ok")
            return redirect(url_for("listado_productos", local=producto["local_id"]))
        except ValueError as e:
            error = str(e)
    v = request.form if request.method == "POST" else producto
    return render_template(
        "producto_form.html", titulo="Editar producto", v=v, error=error, editar=True, producto=producto
    )


@app.route("/productos/<int:producto_id>/baja", methods=["GET", "POST"])
def baja_producto(producto_id):
    producto = producto_or_404(producto_id)
    if request.method == "POST":
        db.dar_de_baja(conexion(), producto_id)
        flash("Producto dado de baja.", "ok")
        return redirect(url_for("listado_productos", local=producto["local_id"]))
    return render_template("confirmar_baja.html", producto=producto)


@app.get("/productos/<int:producto_id>/historial")
def historial_producto(producto_id):
    producto = producto_or_404(producto_id)
    return render_template(
        "historial.html", producto=producto, movimientos=db.historial(conexion(), producto_id)
    )


@app.route("/movimientos/nuevo", methods=["GET", "POST"])
def nuevo_movimiento():
    conn = conexion()
    tipo = request.values.get("tipo", "entrada")
    error = None
    if request.method == "POST":
        try:
            local_id = db.registrar_movimiento(
                conn,
                request.form.get("producto_id"),
                request.form.get("tipo"),
                request.form.get("cantidad"),
                request.form.get("fecha"),
            )
            flash("Movimiento registrado.", "ok")
            return redirect(url_for("listado_productos", local=local_id))
        except ValueError as e:
            error = str(e)
    v = request.form if request.method == "POST" else {"tipo": tipo, "fecha": date.today().isoformat()}
    return render_template(
        "movimiento_form.html",
        productos=db.listar_productos(conn),
        v=v,
        error=error,
    )


@app.get("/compras")
def lista_compras():
    local = local_param()
    return render_template(
        "compras.html", items=db.listar_alertas(conexion(), local), local=local
    )


@app.get("/inventario.xlsx")
def exportar_inventario():
    filas = db.listar_productos(conexion(), local_param())
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"
    ws.append(["Nombre", "Categoría", "Local", "Stock", "Stock mínimo"])
    for p in filas:
        ws.append([p["nombre"], p["categoria"], p["local"], p["stock"], p["stock_minimo"]])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="inventario.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.cli.command("init-db")
def init_db_cmd():
    db.crear_base()
    print("Base de datos lista.")
