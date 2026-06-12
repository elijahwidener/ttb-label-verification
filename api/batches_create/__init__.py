import azure.functions as func

from shared.db import get_conn
from shared.http import error_response, json_response, parse_json_body

MAX_BATCH_SIZE = 20  # prototype cap


def main(req: func.HttpRequest) -> func.HttpResponse:
    body, err = parse_json_body(req)
    if err:
        return err

    total = body.get("total")
    note = (body.get("submitter_note") or "").strip() or None
    if not isinstance(total, int) or not (1 <= total <= MAX_BATCH_SIZE):
        return error_response("invalid_total", 422, notification={
            "level": "error",
            "title": "Batch too large",
            "message": f"Batches are limited to {MAX_BATCH_SIZE} applications in this prototype.",
        })

    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO batches (total, submitter_note) VALUES (%s, %s) RETURNING id",
            (total, note),
        ).fetchone()
        conn.commit()

    return json_response({"batch_id": str(row["id"])}, 201)
