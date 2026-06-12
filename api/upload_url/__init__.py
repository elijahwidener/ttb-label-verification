import azure.functions as func

from shared import blob
from shared.http import error_response, json_response, parse_json_body

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def main(req: func.HttpRequest) -> func.HttpResponse:
    body, err = parse_json_body(req)
    if err:
        return err

    filename = body.get("filename") or ""
    content_type = body.get("content_type") or ""
    side = body.get("side") or ""

    if side not in ("front", "back"):
        return error_response("invalid_side", 422)
    if content_type not in ALLOWED_CONTENT_TYPES:
        return error_response("unsupported_content_type", 422, notification={
            "level": "error",
            "title": "Unsupported file type",
            "message": "Please upload a JPEG, PNG, or WEBP image.",
        })
    if not filename:
        return error_response("missing_filename", 422)

    return json_response(blob.make_upload_sas(filename, content_type, side))
