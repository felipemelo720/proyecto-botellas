import os
from datetime import date

import pymysql
from pymysql.cursors import DictCursor

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def config():
    return dict(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "botellas"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        # lecturas ven datos ya confirmados por otras conexiones
        init_command="SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED",
    )


def conectar():
    return pymysql.connect(**config())


def crear_base():
    cfg = config()
    nombre = cfg.pop("database")
    servidor = pymysql.connect(**cfg, autocommit=True)
    with servidor.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{nombre}` CHARACTER SET utf8mb4")
    servidor.close()

    conn = conectar()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sentencias = [s.strip() for s in f.read().split(";") if s.strip()]
    with conn.cursor() as cur:
        for sentencia in sentencias:
            cur.execute(sentencia)
    conn.commit()
    conn.close()


def texto(valor, nombre):
    t = (valor or "").strip()
    if not t:
        raise ValueError(f"Falta el campo {nombre}.")
    return t


def entero(valor, nombre, minimo):
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ValueError(f"El campo {nombre} debe ser un número entero.")
    if n < minimo:
        raise ValueError(f"El campo {nombre} debe ser mayor o igual a {minimo}.")
    return n


def fecha_valida(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValueError("La fecha no es válida.")


def listar_locales(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, nombre FROM locales ORDER BY nombre")
        return cur.fetchall()


def obtener_producto(conn, producto_id):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.id, p.nombre, p.categoria, p.stock, p.stock_minimo, p.local_id,
                      l.nombre AS local
               FROM productos p JOIN locales l ON l.id = p.local_id
               WHERE p.id = %s AND p.activo = 1""",
            (producto_id,),
        )
        return cur.fetchone()


def listar_productos(conn, local_id=None, q=None):
    sql = """SELECT p.id, p.nombre, p.categoria, p.stock, p.stock_minimo, p.local_id,
                    l.nombre AS local, (p.stock <= p.stock_minimo) AS alerta
             FROM productos p JOIN locales l ON l.id = p.local_id
             WHERE p.activo = 1"""
    params = []
    if local_id:
        sql += " AND p.local_id = %s"
        params.append(local_id)
    if q:
        sql += " AND (p.nombre LIKE %s OR p.categoria LIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY p.nombre"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def listar_alertas(conn, local_id=None):
    # shortcut: sugerido es minimo - stock sin redondear a lotes, subir si el proveedor vende por caja
    sql = """SELECT p.id, p.nombre, p.categoria, p.stock, p.stock_minimo,
                    l.nombre AS local, p.stock_minimo - p.stock AS sugerido
             FROM productos p JOIN locales l ON l.id = p.local_id
             WHERE p.activo = 1 AND p.stock <= p.stock_minimo"""
    params = []
    if local_id:
        sql += " AND p.local_id = %s"
        params.append(local_id)
    sql += " ORDER BY l.nombre, p.nombre"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def crear_producto(conn, nombre, categoria, local_id, stock, stock_minimo):
    datos = validar_producto(nombre, categoria, stock_minimo)
    stock = entero(stock, "stock", 0)
    local_id = entero(local_id, "local", 1)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO productos (nombre, categoria, local_id, stock, stock_minimo)
                   VALUES (%s, %s, %s, %s, %s)""",
                (datos["nombre"], datos["categoria"], local_id, stock, datos["stock_minimo"]),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def editar_producto(conn, producto_id, nombre, categoria, stock_minimo):
    datos = validar_producto(nombre, categoria, stock_minimo)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE productos SET nombre = %s, categoria = %s, stock_minimo = %s
                   WHERE id = %s AND activo = 1""",
                (datos["nombre"], datos["categoria"], datos["stock_minimo"], producto_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def validar_producto(nombre, categoria, stock_minimo):
    return dict(
        nombre=texto(nombre, "nombre"),
        categoria=texto(categoria, "categoría"),
        stock_minimo=entero(stock_minimo, "stock mínimo", 0),
    )


def dar_de_baja(conn, producto_id):
    # baja logica: el historial de movimientos se conserva
    with conn.cursor() as cur:
        cur.execute("UPDATE productos SET activo = 0 WHERE id = %s AND activo = 1", (producto_id,))
        afectados = cur.rowcount
    conn.commit()
    return afectados


def registrar_movimiento(conn, producto_id, tipo, cantidad, fecha):
    if tipo not in ("entrada", "salida"):
        raise ValueError("El tipo de movimiento no es válido.")
    producto_id = entero(producto_id, "producto", 1)
    cantidad = entero(cantidad, "cantidad", 1)
    fecha = fecha_valida(fecha)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT stock, local_id FROM productos WHERE id = %s AND activo = 1 FOR UPDATE",
                (producto_id,),
            )
            producto = cur.fetchone()
            if not producto:
                raise ValueError("El producto no existe.")
            if tipo == "salida":
                if cantidad > producto["stock"]:
                    raise ValueError(
                        f"Salida rechazada. Stock disponible: {producto['stock']}."
                    )
                nuevo_stock = producto["stock"] - cantidad
            else:
                nuevo_stock = producto["stock"] + cantidad
            cur.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))
            cur.execute(
                """INSERT INTO movimientos (producto_id, local_id, tipo, cantidad, fecha)
                   VALUES (%s, %s, %s, %s, %s)""",
                (producto_id, producto["local_id"], tipo, cantidad, fecha),
            )
        conn.commit()
        return producto["local_id"]
    except Exception:
        conn.rollback()
        raise


def historial(conn, producto_id):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT m.tipo, m.cantidad, m.fecha, l.nombre AS local
               FROM movimientos m JOIN locales l ON l.id = m.local_id
               WHERE m.producto_id = %s
               ORDER BY m.fecha DESC, m.id DESC""",
            (producto_id,),
        )
        return cur.fetchall()
