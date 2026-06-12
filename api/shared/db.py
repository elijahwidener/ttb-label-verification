import os
import threading
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

_schema_lock = threading.Lock()
_schema_ensured = False


def get_conn() -> psycopg.Connection:
    """One connection per request. Serverless functions are short-lived; a
    connection pool buys little on the Burstable tier and adds failure modes."""
    url = os.environ["POSTGRES_URL"]
    conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
    _ensure_schema(conn)
    return conn


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
