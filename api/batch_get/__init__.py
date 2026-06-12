import uuid

import azure.functions as func

from shared.db import get_conn
from shared.http import error_response, json_response
from shared.models import serialize_application


def main(req: func.HttpRequest) -> func.HttpResponse:
    batch_id = req.route_params.get("batch_id")
    try:
        uuid.UUID(batch_id)
    except (TypeError, ValueError):
        return error_response("invalid_id", 422)

    with get_conn() as conn:
        batch = conn.execute(
            "SELECT * FROM batches WHERE id = %s", (batch_id,)
        ).fetchone()
        if not batch:
            return error_response("not_found", 404)
        rows = conn.execute(
            "SELECT * FROM applications WHERE batch_id = %s ORDER BY submitted_at ASC",
            (batch_id,),
        ).fetchall()

    return json_response({
        "batch_id": str(batch["id"]),
        "created_at": batch["created_at"].isoformat(),
        "total": batch["total"],
        "submitter_note": batch["submitter_note"],
        "completed": len(rows),
        "rejected": sum(1 for r in rows if r["overall_status"] == "FAIL"),
        "applications": [serialize_application(r) for r in rows],
    })
