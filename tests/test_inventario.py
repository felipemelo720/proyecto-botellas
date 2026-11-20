import io

import openpyxl
from datetime import date

import db
from tests.conftest import local_id


def crear(conn, nombre="Pisco", categoria="Licor", local="Osorno", stock=10, minimo=3):
    db.crear_producto(conn, nombre, categoria, local_id(conn, local), stock, minimo)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM productos WHERE nombre = %s", (nombre,))
        return cur.fetchone()["id"]


def stock_de(conn, producto_id):
    with conn.cursor() as cur:
        cur.execute("SELECT stock FROM productos WHERE id = %s", (producto_id,))
        return cur.fetchone()["stock"]


# HU01
def test_crear_producto_aparece_en_listado(client, conn):
    r = client.post("/productos/nuevo", data=dict(
        nombre="Vino tinto", categoria="Vino", local_id=local_id(conn, "Temuco"),
        stock="8", stock_minimo="2"))
    assert r.status_code == 302
    assert b"Vino tinto" in client.get("/productos?local=" + str(local_id(conn, "Temuco"))).data


def test_crear_producto_rechaza_campo_vacio_y_negativos(client, conn):
    r = client.post("/productos/nuevo", data=dict(
        nombre="", categoria="Vino", local_id=local_id(conn, "Temuco"), stock="1", stock_minimo="1"))
    assert b"Falta el campo nombre." in r.data
    r = client.post("/productos/nuevo", data=dict(
        nombre="Ron", categoria="Licor", local_id=local_id(conn, "Temuco"), stock="-1", stock_minimo="1"))
    assert b"debe ser mayor o igual a 0" in r.data
    assert not db.listar_productos(conn)


# HU02
def test_editar_nombre_y_minimo(client, conn):
    pid = crear(conn)
    client.post(f"/productos/{pid}/editar", data=dict(nombre="Pisco Reservado", categoria="Licor", stock_minimo="5"))
    p = db.obtener_producto(conn, pid)
    assert p["nombre"] == "Pisco Reservado" and p["stock_minimo"] == 5


# HU03 / HU04 / HU05
def test_entrada_aumenta_stock_y_salida_descuenta(conn):
    pid = crear(conn, stock=10)
    db.registrar_movimiento(conn, pid, "entrada", "5", "2026-11-10")
    assert stock_de(conn, pid) == 15
    db.registrar_movimiento(conn, pid, "salida", "4", "2026-11-11")
    assert stock_de(conn, pid) == 11


def test_salida_mayor_al_stock_se_rechaza(client, conn):
    pid = crear(conn, stock=5)
    r = client.post("/movimientos/nuevo", data=dict(
        producto_id=pid, tipo="salida", cantidad="6", fecha="2026-11-12"))
    assert b"Stock disponible: 5." in r.data
    assert stock_de(conn, pid) == 5


def test_fecha_invalida_rechazada(conn):
    pid = crear(conn)
    try:
        db.registrar_movimiento(conn, pid, "entrada", "1", "32-13-2026")
        assert False, "debio fallar"
    except ValueError as e:
        assert str(e) == "La fecha no es válida."


# HU06
def test_baja_pide_confirmacion(client, conn):
    pid = crear(conn, nombre="Ron Añejo")
    r = client.get(f"/productos/{pid}/baja")
    assert "Sí, dar de baja".encode() in r.data
    assert db.obtener_producto(conn, pid) is not None  # cancelar no cambia nada


def test_baja_confirmada_oculta_producto(client, conn):
    pid = crear(conn, nombre="Ron Añejo")
    client.post(f"/productos/{pid}/baja")
    assert db.obtener_producto(conn, pid) is None
    assert b"Ron A" not in client.get("/productos").data


# HU07
def test_filtro_por_local(conn):
    crear(conn, nombre="Solo Osorno", local="Osorno")
    crear(conn, nombre="Solo Temuco", local="Temuco")
    nombres = [p["nombre"] for p in db.listar_productos(conn, local_id(conn, "Temuco"))]
    assert nombres == ["Solo Temuco"]


# HU08
def test_alerta_marca_fila_y_cuenta(client, conn):
    crear(conn, nombre="Bajo", stock=2, minimo=3)
    crear(conn, nombre="Sano", stock=9, minimo=3)
    r = client.get("/productos")
    assert b'class="alerta"' in r.data
    assert "1 producto(s) en o bajo su stock mínimo.".encode() in r.data


def test_alerta_se_actualiza_tras_salida(conn):
    pid = crear(conn, stock=4, minimo=3)
    assert len(db.listar_alertas(conn)) == 0
    db.registrar_movimiento(conn, pid, "salida", "2", "2026-11-13")
    assert len(db.listar_alertas(conn)) == 1


# HU09
def test_historial_mas_reciente_primero(conn):
    pid = crear(conn, stock=10)
    db.registrar_movimiento(conn, pid, "entrada", "1", "2026-11-01")
    db.registrar_movimiento(conn, pid, "salida", "2", "2026-11-05")
    db.registrar_movimiento(conn, pid, "entrada", "3", "2026-11-03")
    fechas = [m["fecha"] for m in db.historial(conn, pid)]
    assert fechas == [date(2026, 11, 5), date(2026, 11, 3), date(2026, 11, 1)]


# HU10
def test_lista_compras_sugerido_llega_al_minimo(conn):
    crear(conn, nombre="Escaso", stock=1, minimo=6, local="Valdivia")
    crear(conn, nombre="Ok", stock=10, minimo=6, local="Valdivia")
    items = db.listar_alertas(conn, local_id(conn, "Valdivia"))
    assert [(i["nombre"], i["sugerido"]) for i in items] == [("Escaso", 5)]


# HU11
def test_exportar_excel_con_tildes_y_enie(client, conn):
    crear(conn, nombre="Piña colada", categoria="Bebida ñandú")
    r = client.get("/inventario.xlsx")
    assert r.status_code == 200
    ws = openpyxl.load_workbook(io.BytesIO(r.data)).active
    fila = [c.value for c in ws[2]]
    assert fila[0] == "Piña colada" and fila[1] == "Bebida ñandú"


# HU12
def test_buscar_por_nombre_o_categoria_y_sin_resultados(client, conn):
    crear(conn, nombre="Gin Tanqueray", categoria="Licor")
    crear(conn, nombre="Agua mineral", categoria="Bebida")
    assert [p["nombre"] for p in db.listar_productos(conn, q="licor")] == ["Gin Tanqueray"]
    assert b"No hay productos." in client.get("/productos?q=zzz").data


# UX: feedback, badge, tarjetas y stock disponible
def test_flash_tras_registrar_y_badge_bajo_minimo(client, conn):
    r = client.post("/productos/nuevo", data=dict(
        nombre="Ron Viejo", categoria="Licor", local_id=local_id(conn, "Osorno"),
        stock="1", stock_minimo="4"), follow_redirects=True)
    assert "Producto registrado.".encode() in r.data
    assert "Bajo mínimo".encode() in r.data
    assert b'class="tarjetas"' in r.data


def test_movimiento_muestra_stock_disponible(client, conn):
    pid = crear(conn, stock=7)
    r = client.get("/movimientos/nuevo?tipo=salida")
    assert f'data-stock="7"'.encode() in r.data and str(pid).encode() in r.data
