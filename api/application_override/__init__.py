"""POST /api/applications/{id}/override — submitter disputes an auto-FAIL.

Moves the application to WARN (agent queue) with the original FAIL recorded.
No Claude re-check: the agent judges using the existing extraction plus the
submitter's explanation.
"""

import uuid

import azure.functions as func

from shared.db import get_conn
from shared.http import error_response, json_response, parse_json_body
from shared.models import serialize_application

MIN_EXPLANATION_CHARS = 10


def main(req: func.HttpRequest) -> func.HttpResponse:
    app_id = req.route_params.get("id")
    try:
        uuid.UUID(app_id)
    except (TypeError, ValueError):
        return error_response("invalid_id", 422)

    body, err = parse_json_body(req)
    if err:
        return err

    attestation = body.get("attestation") is True
    explanation = (body.get("explanation") or "").strip()
    if not attestation or len(explanation) < MIN_EXPLANATION_CHARS:
        return error_response("invalid_override", 400, notification={
            "level": "error",
            "title": "Override incomplete",
            "message": "Please check the attestation box and explain the discrepancy (at least 10 characters).",
        })

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = %s FOR UPDATE", (app_id,)
        ).fetchone()
        if not row:
            return error_response("not_found", 404)
        if row["overall_status"] != "FAIL" or row["decision_source"] != "AUTO":
            return error_response("not_overridable", 400, notification={
                "level": "error",
                "title": "Cannot request review",
                "message": "Only automatically rejected applications can be disputed.",
            })
        if row["override_at"] is not None:
            return error_response("already_overridden", 400, notification={
                "level": "error",
                "title": "Already submitted",
                "message": "A review has already been requested for this application.",
            })

        updated = conn.execute(
            """
            UPDATE applications SET
                original_status = 'FAIL',
                overall_status = 'WARN',
                decision = NULL,
                decision_source = NULL,
                decision_at = NULL,
                override_attestation = TRUE,
                override_explanation = %s,
                override_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (explanation, app_id),
        ).fetchone()
        conn.commit()

    result = serialize_application(updated)
    result["notification"] = {
        "level": "info",
        "title": "Review requested",
        "message": "Your override has been submitted. An agent will review and notify you of the final decision.",
    }
    return json_response(result)
