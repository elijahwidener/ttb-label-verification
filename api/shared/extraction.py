"""AI extraction: Pillow preprocessing + a single Claude vision call with both
label images. Claude's job is OCR only — comparison happens in validation.py."""

import base64
import io
import json
import logging
import os

import anthropic
from PIL import Image, UnidentifiedImageError

from .prompts import SYSTEM_PROMPT

MODEL = "claude-sonnet-4-6"
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_DIMENSION = 2048
JPEG_QUALITY = 85
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

logger = logging.getLogger("ttb.extraction")


class ExtractionUnavailable(Exception):
    """Claude API unreachable after one retry → surface as HTTP 503."""


class ImagePreprocessError(Exception):
    """Image is not a valid JPEG/PNG/WEBP."""


def preprocess_image(data: bytes) -> bytes:
    """Validate format, resize to <=2048px on the long side, re-encode as
    JPEG q85. Returns JPEG bytes ready for base64."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImagePreprocessError("File is not a readable image.") from exc
    if (img.format or "").upper() not in ALLOWED_FORMATS:
        raise ImagePreprocessError(
            f"Unsupported image format '{img.format}'. Use JPEG, PNG, or WEBP."
        )
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY)
    return out.getvalue()


def _image_block(jpeg_bytes: bytes) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.standard_b64encode(jpeg_bytes).decode("utf-8"),
        },
    }


def _call_claude(front_jpeg: bytes, back_jpeg: bytes):
    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,  # retry policy is ours: one retry on timeout/529 only
    )
    return client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    _image_block(front_jpeg),
                    _image_block(back_jpeg),
                    {
                        "type": "text",
                        "text": "The first image is the FRONT label, the second is the BACK label. Extract now.",
                    },
                ],
            }
        ],
    )


def extract(front_jpeg: bytes, back_jpeg: bytes) -> dict | None:
    """Returns the parsed extraction dict, or None when Claude returned
    malformed JSON (caller treats all fields as WARN). Raises
    ExtractionUnavailable when the API is down after one retry."""
    last_exc = None
    for attempt in range(2):
        try:
            response = _call_claude(front_jpeg, back_jpeg)
            break
        except anthropic.APITimeoutError as exc:
            last_exc = exc
        except anthropic.APIStatusError as exc:
            if exc.status_code == 529:
                last_exc = exc
            else:
                raise ExtractionUnavailable(str(exc)) from exc
        except anthropic.APIConnectionError as exc:
            last_exc = exc
    else:
        raise ExtractionUnavailable(str(last_exc))

    raw = "".join(b.text for b in response.content if b.type == "text").strip()
    # Defensive: strip markdown fences despite prompt instructions.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("not an object")
        return parsed
    except (ValueError, json.JSONDecodeError):
        logger.error("Malformed extraction response from Claude: %r", raw[:2000])
        return None
