"""POST /api/applications/{id}/decide — agent approves or rejects.

WARN with no decision -> decision_source AGENT.
Overriding an existing AUTO decision -> decision_source AGENT_OVERRIDE.
Decisions are soft: DB-only, no COLA write-back, no notifications.
"""

import uuid

import azure.functions as func

from shared.db import get_conn
from shared.http import error_response, json_response, parse_json_body
from shared.models import serialize_application


def main(req: func.HttpRequest) -> func.HttpResponse:
    app_id = req.route_params.get("id")
    try:
        uuid.UUID(app_id)
    except (TypeError, ValueError):
        return error_response("invalid_id", 422)

    body, err = parse_json_body(req)
    if err:
        return err

    decision = body.get("decision")
    comment = (body.get("comment") or "").strip() or None
    if decision not in ("APPROVED", "REJECTED"):
        return error_response("invalid_decision", 422)

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = %s FOR UPDATE", (app_id,)
        ).fetchone()
        if not row:
            return error_response("not_found", 404)

        if row["decision"] is None:
            source = "AGENT"
        elif row["decision_source"] == "AUTO":
            source = "AGENT_OVERRIDE"
        else:
            return error_response("already_decided", 400, notification={
                "level": "error",
                "title": "Already decided",
                "message": "An agent has already made a final decision on this application.",
            })

        updated = conn.execute(
            """
            UPDATE applications SET
                decision = %s,
                decision_source = %s,
                decision_at = NOW(),
                decision_comment = %s
            WHERE id = %s
            RETURNING *
            """,
            (decision, source, comment, app_id),
        ).fetchone()
        conn.commit()

    return json_response(serialize_application(updated))
