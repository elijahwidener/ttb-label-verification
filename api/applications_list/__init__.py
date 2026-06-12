"""GET /api/applications

Default: WARN with no decision (the agent queue), oldest first.
Query params: status=PASS|WARN|FAIL, decided=true|false, source=AUTO|AGENT,
limit, offset. `source` is an addition to the contract so the agent UI's
Auto-Decided and History tabs can filter server-side.
"""

import azure.functions as func

from shared.db import get_conn
from shared.http import error_response, json_response
from shared.models import serialize_application


def main(req: func.HttpRequest) -> func.HttpResponse:
    status = req.params.get("status")
    decided = req.params.get("decided")
    source = req.params.get("source")
    try:
        limit = min(int(req.params.get("limit", 50)), 200)
        offset = max(int(req.params.get("offset", 0)), 0)
    except ValueError:
        return error_response("invalid_pagination", 422)

    where, params = [], []
    if status:
        if status not in ("PASS", "WARN", "FAIL"):
            return error_response("invalid_status", 422)
        where.append("overall_status = %s")
        params.append(status)
    if decided == "true":
        where.append("decision IS NOT NULL")
    elif decided == "false":
        where.append("decision IS NULL")
    if source == "AUTO":
        where.append("decision_source = 'AUTO'")
    elif source == "AGENT":
        where.append("decision_source IN ('AGENT','AGENT_OVERRIDE')")

    if not status and not decided and not source:
        # Default agent queue view
        where = ["overall_status = 'WARN'", "decision IS NULL"]
        params = []

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM applications {where_sql}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT * FROM applications {where_sql}
            ORDER BY submitted_at ASC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        ).fetchall()

    return json_response({
        "applications": [serialize_application(r) for r in rows],
        "total": total,
    })
