import os
import threading
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

_local = threading.local()
_schema_lock = threading.Lock()
_schema_ensured = False


def _connect() -> psycopg.Connection:
    conn = psycopg.connect(
        os.environ["POSTGRES_URL"], row_factory=dict_row, connect_timeout=10
    )
    _ensure_schema(conn)
    return conn


def _healthy(conn: psycopg.Connection) -> bool:
    try:
        conn.execute("SELECT 1")
        conn.commit()
        return True
    except Exception:
        return False


@contextmanager
def get_conn():
    """Yields a thread-cached connection. Exit commits (or rolls back on error)
    but does NOT close: TLS + auth to Postgres costs hundreds of ms, which
    dominated request latency when every call reconnected. Thread-local keeps
    it safe if the Functions worker runs invocations on multiple threads; the
    cheap SELECT 1 health check replaces stale connections after idle."""
    conn = getattr(_local, "conn", None)
    if conn is None or conn.closed or not _healthy(conn):
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        conn = _connect()
        _local.conn = conn
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def _ensure_schema(conn: psycopg.Connection) -> None:
    """Idempotently apply schema on first use per worker process. Removes the
    manual 'run psql' deployment step; db/schema.sql remains canonical."""
    global _schema_ensured
    if _schema_ensured:
        return
    with _schema_lock:
        if _schema_ensured:
            return
        sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        _schema_ensured = True


def jsonb(value) -> Json:
    return Json(value)
