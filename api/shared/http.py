import json
import azure.functions as func


def json_response(body: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, default=str),
        status_code=status,
        mimetype="application/json",
    )


def error_response(message: str, status: int = 400, **extra) -> func.HttpResponse:
    body = {"error": message}
    body.update(extra)
    return json_response(body, status)


def parse_json_body(req: func.HttpRequest):
    """Returns (dict, None) or (None, HttpResponse 422)."""
    try:
        body = req.get_json()
    except ValueError:
        return None, error_response("invalid_json", 422, notification={
            "level": "error",
            "title": "Invalid request",
            "message": "The request body was not valid JSON.",
        })
    if not isinstance(body, dict):
        return None, error_response("invalid_json", 422)
    return body, None
