"""Field definitions and serializers. The DB schema (db/schema.sql) is the
source of truth for structure; these mirror it."""

REQUIRED_APPLICATION_FIELDS = [
    "brand_name",
    "class_type",
    "alcohol_content",
    "net_contents",
    "producer_name",
    "producer_address",
]

OPTIONAL_APPLICATION_FIELDS = ["country_of_origin"]

ALL_APPLICATION_FIELDS = REQUIRED_APPLICATION_FIELDS + OPTIONAL_APPLICATION_FIELDS

# Fields the validation engine produces results for (application fields plus
# the government warning, which is validated against the statutory text).
VALIDATED_FIELDS = ALL_APPLICATION_FIELDS + ["government_warning"]

FIELD_LABELS = {
    "brand_name": "Brand name",
    "class_type": "Class / type",
    "alcohol_content": "Alcohol content",
    "net_contents": "Net contents",
    "producer_name": "Producer name",
    "producer_address": "Producer address",
    "country_of_origin": "Country of origin",
    "government_warning": "Government warning",
}


def notification_for_status(overall_status: str) -> dict:
    if overall_status == "PASS":
        return {
            "level": "success",
            "title": "Application approved",
            "message": "Your submission has been auto-approved. No further action needed.",
        }
    if overall_status == "FAIL":
        return {
            "level": "error",
            "title": "Application rejected",
            "message": (
                "One or more fields did not match the label. See details below. "
                "If you believe this is incorrect, you can request human review."
            ),
        }
    return {
        "level": "info",
        "title": "Application received — pending review",
        "message": "Some fields require human review. An agent will make the final decision.",
    }


def serialize_application(row: dict, front_image_url: str | None = None,
                          back_image_url: str | None = None) -> dict:
    """Serialize a DB row (dict_row) to the API shape. Image URLs, when
    provided, are short-lived read-SAS URLs (blob containers are private)."""
    out = {
        "id": str(row["id"]),
        "submitted_at": row["submitted_at"].isoformat() if row.get("submitted_at") else None,
        "brand_name": row["brand_name"],
        "class_type": row["class_type"],
        "alcohol_content": row["alcohol_content"],
        "net_contents": row["net_contents"],
        "producer_name": row["producer_name"],
        "producer_address": row["producer_address"],
        "country_of_origin": row["country_of_origin"],
        "overall_status": row["overall_status"],
        "field_results": row["field_results"],
        "front_image_quality": row["front_image_quality"],
        "back_image_quality": row["back_image_quality"],
        "processing_ms": row["processing_ms"],
        "decision": row["decision"],
        "decision_source": row["decision_source"],
        "decision_at": row["decision_at"].isoformat() if row.get("decision_at") else None,
        "decision_comment": row["decision_comment"],
        "override_attestation": row["override_attestation"],
        "override_explanation": row["override_explanation"],
        "override_at": row["override_at"].isoformat() if row.get("override_at") else None,
        "original_status": row["original_status"],
        "batch_id": str(row["batch_id"]) if row.get("batch_id") else None,
        "front_image_deleted": row["front_image_deleted"],
        "back_image_deleted": row["back_image_deleted"],
    }
    if front_image_url is not None:
        out["front_image_url"] = front_image_url
    if back_image_url is not None:
        out["back_image_url"] = back_image_url
    return out
