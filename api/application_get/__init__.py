"""GET /api/applications/{id} — full detail, including short-lived read-SAS
image URLs so the agent can view the actual label (containers are private)."""

import uuid

import azure.functions as func

from shared import blob
from shared.db import get_conn
from shared.http import error_response, json_response
from shared.models import serialize_application


def main(req: func.HttpRequest) -> func.HttpResponse:
    app_id = req.route_params.get("id")
    try:
        uuid.UUID(app_id)
    except (TypeError, ValueError):
        return error_response("invalid_id", 422)

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = %s", (app_id,)
        ).fetchone()

    if not row:
        return error_response("not_found", 404)

    front_sas = None if row["front_image_deleted"] else blob.make_read_sas(row["front_image_blob_url"])
    back_sas = None if row["back_image_deleted"] else blob.make_read_sas(row["back_image_blob_url"])

    return json_response(serialize_application(row, front_sas, back_sas))
