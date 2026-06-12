import azure.functions as func

from shared.http import json_response


def main(req: func.HttpRequest) -> func.HttpResponse:
    return json_response({"status": "ok"})
