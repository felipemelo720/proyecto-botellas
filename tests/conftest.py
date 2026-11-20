import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# Las pruebas nunca tocan la base real
os.environ["DB_NAME"] = "botellas_test"
os.environ.setdefault("DB_PORT", "3306")

import pytest  # noqa: E402

import app as app_module  # noqa: E402
import db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def base_lista():
    db.crear_base()


@pytest.fixture
def conn(base_lista):
    c = db.conectar()
    with c.cursor() as cur:
        cur.execute("DELETE FROM movimientos")
        cur.execute("DELETE FROM productos")
    c.commit()
    yield c
    c.close()


@pytest.fixture
def client(conn):
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


def local_id(conn, nombre):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM locales WHERE nombre = %s", (nombre,))
        return cur.fetchone()["id"]
