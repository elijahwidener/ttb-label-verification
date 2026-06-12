"""POST /api/submit — the intake pipeline.

quarantine download -> Pillow preprocess -> Claude (quality + extraction in one
call) -> unusable? delete + 400 / usable? promote to labels -> validation
engine -> persist with auto-decision -> respond with the verification result.
"""

import logging
import time

import azure.functions as func

from shared import blob, extraction, validation
from shared.db import get_conn, jsonb
from shared.http import error_response, json_response, parse_json_body
from shared.models import (
    ALL_APPLICATION_FIELDS,
    REQUIRED_APPLICATION_FIELDS,
    notification_for_status,
)

logger = logging.getLogger("ttb.submit")


def main(req: func.HttpRequest) -> func.HttpResponse:
    started = time.monotonic()
    body, err = parse_json_body(req)
    if err:
        return err

    front_url = body.get("front_blob_url") or ""
    back_url = body.get("back_blob_url") or ""
    app_data = body.get("application_data") or {}
    batch_id = body.get("batch_id") or None

    missing = [f for f in REQUIRED_APPLICATION_FIELDS if not (app_data.get(f) or "").strip()]
    if not front_url or not back_url:
        missing.append("front_blob_url/back_blob_url")
    if missing:
        return error_response("missing_fields", 422, fields=missing, notification={
            "level": "error",
            "title": "Missing information",
            "message": "Please fill in all required fields and upload both label images.",
        })

    # ---- download from quarantine
    try:
        front_raw = blob.download_quarantine_blob(front_url)
        back_raw = blob.download_quarantine_blob(back_url)
    except ValueError as exc:
        return error_response("invalid_blob_url", 422, detail=str(exc))
    except Exception:
        logger.exception("quarantine download failed")
        return error_response("blob_download_failed", 422, notification={
            "level": "error",
            "title": "Upload not found",
            "message": "We could not find your uploaded images. Please re-upload and try again.",
        })

    # ---- Pillow preprocessing (format gate happens here, before Claude)
    failed_side = None
    front_issue = back_issue = ""
    try:
        front_jpeg = extraction.preprocess_image(front_raw)
    except extraction.ImagePreprocessError as exc:
        failed_side, front_issue = "front", str(exc)
    try:
        back_jpeg = extraction.preprocess_image(back_raw)
    except extraction.ImagePreprocessError as exc:
        back_issue = str(exc)
        failed_side = "both" if failed_side == "front" else "back"
    if failed_side:
        blob.delete_blob_quiet(front_url)
        blob.delete_blob_quiet(back_url)
        side_label = {"front": "Front", "back": "Back", "both": "Both"}[failed_side]
        return json_response({
            "error": "image_unusable",
            "failed_side": failed_side,
            "notification": {
                "level": "error",
                "title": f"{side_label} image cannot be read",
                "message": (front_issue or back_issue) + " Please re-upload a valid photo.",
            },
        }, 400)

    # ---- Claude: quality check + extraction in one call
    try:
        extracted = extraction.extract(front_jpeg, back_jpeg)
    except extraction.ExtractionUnavailable:
        logger.exception("Claude unavailable after retry")
        return error_response("ai_unavailable", 503, notification={
            "level": "error",
            "title": "Service temporarily unavailable",
            "message": "The verification service is temporarily unavailable. Your images were not stored. Please try again in a few minutes.",
        })

    if extracted is None:
        # Malformed JSON from Claude: all fields WARN, route to agent queue.
        overall, field_results = validation.all_warn_results(
            app_data,
            "The automated reading of this label could not be completed. An agent will review the label manually.",
        )
        front_quality = {"usable": True, "issues": "extraction response malformed; manual review required"}
        back_quality = dict(front_quality)
    else:
        front_quality = extracted.get("front_image_quality") or {}
        back_quality = extracted.get("back_image_quality") or {}
        front_ok = bool(front_quality.get("usable", True))
        back_ok = bool(back_quality.get("usable", True))
        if not front_ok or not back_ok:
            blob.delete_blob_quiet(front_url)
            blob.delete_blob_quiet(back_url)
            failed_side = "both" if (not front_ok and not back_ok) else ("front" if not front_ok else "back")
            issues = front_quality.get("issues") if not front_ok else back_quality.get("issues")
            side_label = {"front": "Front", "back": "Back", "both": "Both"}[failed_side]
            return json_response({
                "error": "image_unusable",
                "failed_side": failed_side,
                "notification": {
                    "level": "error",
                    "title": f"{side_label} image cannot be read",
                    "message": (issues or "The image is not clear enough to read.")
                               + f" Please re-upload a clearer photo of the {failed_side if failed_side != 'both' else 'front and back'}.",
                },
            }, 400)
        overall, field_results = validation.validate(app_data, extracted)

    # ---- promote images to permanent storage
    try:
        front_perm = blob.promote_to_labels(front_url, front_jpeg)
        back_perm = blob.promote_to_labels(back_url, back_jpeg)
    except Exception:
        logger.exception("blob promotion failed")
        return error_response("storage_error", 503, notification={
            "level": "error",
            "title": "Storage error",
            "message": "We could not store your images. Please try again.",
        })

    # ---- auto-decision + persist
    decision = decision_source = None
    if overall == "PASS":
        decision, decision_source = "APPROVED", "AUTO"
    elif overall == "FAIL":
        decision, decision_source = "REJECTED", "AUTO"

    processing_ms = int((time.monotonic() - started) * 1000)

    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO applications (
                front_image_blob_url, back_image_blob_url,
                brand_name, class_type, alcohol_content, net_contents,
                producer_name, producer_address, country_of_origin,
                overall_status, field_results,
                front_image_quality, back_image_quality, processing_ms,
                decision, decision_source,
                decision_at, batch_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CASE WHEN %s::text IS NOT NULL THEN NOW() END, %s
            )
            RETURNING id
            """,
            (
                front_perm, back_perm,
                app_data["brand_name"].strip(), app_data["class_type"].strip(),
                app_data["alcohol_content"].strip(), app_data["net_contents"].strip(),
                app_data["producer_name"].strip(), app_data["producer_address"].strip(),
                (app_data.get("country_of_origin") or "").strip() or None,
                overall, jsonb(field_results),
                jsonb(front_quality), jsonb(back_quality), processing_ms,
                decision, decision_source,
                decision, batch_id,
            ),
        ).fetchone()
        conn.commit()

    return json_response({
        "application_id": str(row["id"]),
        "overall_status": overall,
        "decision": decision,
        "decision_source": decision_source,
        "notification": notification_for_status(overall),
        "image_quality": {
            "front": front_quality,
            "back": back_quality,
        },
        "fields": field_results,
        "processing_ms": processing_ms,
    }, 201)
