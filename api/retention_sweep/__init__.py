"""POST /api/retention-sweep — deletes label images older than
IMAGE_RETENTION_DAYS and flags the rows, keeping DB and Blob in sync with an
auditable record.

Design note: Azure Static Web Apps *managed* functions support HTTP triggers
only — no timer triggers. So the spec's daily timer is implemented as an HTTP
endpoint invoked by a scheduled GitHub Actions workflow
(.github/workflows/retention-sweep.yml). The blob lifecycle policy (30 days)
is the independent backstop. If RETENTION_SWEEP_KEY is set in app settings,
callers must send it in the x-sweep-key header.
"""

import logging
import os

import azure.functions as func

from shared import blob
from shared.db import get_conn
from shared.http import error_response, json_response

logger = logging.getLogger("ttb.retention")


def main(req: func.HttpRequest) -> func.HttpResponse:
    expected_key = os.environ.get("RETENTION_SWEEP_KEY")
    if expected_key and req.headers.get("x-sweep-key") != expected_key:
        return error_response("forbidden", 403)

    retention_days = int(os.environ.get("IMAGE_RETENTION_DAYS", "30"))

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, front_image_blob_url, back_image_blob_url,
                   front_image_deleted, back_image_deleted
            FROM applications
            WHERE submitted_at < NOW() - make_interval(days => %s)
              AND (front_image_deleted = FALSE OR back_image_deleted = FALSE)
            """,
            (retention_days,),
        ).fetchall()

        swept = 0
        for row in rows:
            if not row["front_image_deleted"]:
                blob.delete_blob_quiet(row["front_image_blob_url"])
            if not row["back_image_deleted"]:
                blob.delete_blob_quiet(row["back_image_blob_url"])
            conn.execute(
                """
                UPDATE applications
                SET front_image_deleted = TRUE, back_image_deleted = TRUE
                WHERE id = %s
                """,
                (row["id"],),
            )
            swept += 1
        conn.commit()

    logger.info("retention sweep: %d applications purged", swept)
    return json_response({"swept": swept, "retention_days": retention_days})
