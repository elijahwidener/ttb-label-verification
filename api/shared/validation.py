"""The validation engine — the core decision layer.

Claude extracts (OCR); this module compares each extracted value against what
the submitter declared and produces an auditable PASS/WARN/FAIL per field with
a plain-language reason. Thresholds are best-guesses from stakeholder
interviews and need empirical tuning (see docs/validation.md)."""

import re

from rapidfuzz import fuzz

from .models import ALL_APPLICATION_FIELDS, FIELD_LABELS, VALIDATED_FIELDS

GOVERNMENT_WARNING_REQUIRED = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

FUZZY_PASS_THRESHOLD = 90
FUZZY_FAIL_THRESHOLD = 60
HIGH_CONFIDENCE = 0.7          # matrix boundary for fuzzy-matched fields (§11.1)
CONFIDENCE_WARN_THRESHOLD = 0.6  # boundary for alcohol_content / net_contents (§11.2)
WARNING_CONFIDENCE_THRESHOLD = 0.5  # government warning readability (§11.2)
ABV_TOLERANCE = 0.1

FUZZY_FIELDS = ["brand_name", "class_type", "producer_name", "producer_address"]

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _fold(text: str) -> str:
    return _norm(text).casefold()


def fuzzy_score(declared: str, extracted: str) -> float:
    """Case-insensitive, whitespace-normalized. ratio catches near-identical
    strings; token_sort_ratio forgives word order (addresses, 'LLC' placement)."""
    a, b = _fold(declared), _fold(extracted)
    return max(fuzz.ratio(a, b), fuzz.token_sort_ratio(a, b))


def _result(field, declared, extracted, confidence, status, reason):
    return {
        "field": field,
        "declared": declared,
        "extracted": extracted,
        "confidence": confidence,
        "status": status,
        "reason": reason,
    }


def _get_extracted(extraction: dict, field: str):
    """Returns (value, confidence, notes) tolerating missing/odd shapes."""
    raw = extraction.get(field) if isinstance(extraction, dict) else None
    if not isinstance(raw, dict):
        return None, 0.0, ""
    value = raw.get("value")
    if value is not None and not isinstance(value, str):
        value = str(value)
    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    notes = raw.get("notes") or ""
    return value, confidence, notes


def _matrix_field(field, declared, value, confidence):
    """Decision matrix (§11.1) for fuzzy-matched fields."""
    label = FIELD_LABELS[field]
    if value is None:
        if confidence >= HIGH_CONFIDENCE:
            return _result(field, declared, None, confidence, FAIL,
                           f"{label} was not found on the label.")
        return _result(field, declared, None, confidence, WARN,
                       f"The AI could not confidently read the {label.lower()} from the label. An agent should check the image.")
    if confidence < HIGH_CONFIDENCE:
        return _result(field, declared, value, confidence, WARN,
                       f"The AI was not confident reading the {label.lower()}. An agent should check the label image.")
    score = fuzzy_score(declared, value)
    if score >= FUZZY_PASS_THRESHOLD:
        return _result(field, declared, value, confidence, PASS,
                       f"{label} matches the application.")
    if score >= FUZZY_FAIL_THRESHOLD:
        return _result(field, declared, value, confidence, WARN,
                       f"{label} on the label is close to the application but not an exact match (similarity {int(score)}/100). An agent should judge whether they mean the same thing.")
    return _result(field, declared, value, confidence, FAIL,
                   f"{label} on the label does not match the application (similarity {int(score)}/100).")


_ABV_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def parse_abv(text: str | None) -> float | None:
    if not text:
        return None
    m = _ABV_RE.search(text)
    return float(m.group(1)) if m else None


def _validate_alcohol(declared, value, confidence):
    field = "alcohol_content"
    declared_abv = parse_abv(declared)
    if declared_abv is None:
        return _result(field, declared, value, confidence, FAIL,
                       "The declared alcohol content could not be parsed as a percentage.")
    if value is None:
        if confidence >= HIGH_CONFIDENCE:
            return _result(field, declared, None, confidence, FAIL,
                           "Alcohol content was not found on the label.")
        return _result(field, declared, None, confidence, WARN,
                       "The AI could not confidently read the alcohol content. An agent should check the image.")
    if confidence < CONFIDENCE_WARN_THRESHOLD:
        return _result(field, declared, value, confidence, WARN,
                       "The AI was not confident reading the alcohol content. An agent should check the label image.")
    extracted_abv = parse_abv(value)
    if extracted_abv is None:
        return _result(field, declared, value, confidence, FAIL,
                       "The alcohol content on the label could not be parsed as a percentage.")
    diff = abs(declared_abv - extracted_abv)
    if diff <= ABV_TOLERANCE:
        return _result(field, declared, value, confidence, PASS,
                       f"Alcohol content matches ({extracted_abv}% on label, {declared_abv}% declared).")
    return _result(field, declared, value, confidence, FAIL,
                   f"Alcohol content differs: label shows {extracted_abv}%, application declares {declared_abv}% (difference {diff:.1f} points, tolerance {ABV_TOLERANCE}).")


_VOLUME_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(ml|cl|l|liter|liters|litre|litres|fl\.?\s*oz|oz)\b",
    re.IGNORECASE,
)
_UNIT_TO_ML = {
    "ml": 1.0, "cl": 10.0, "l": 1000.0,
    "liter": 1000.0, "liters": 1000.0, "litre": 1000.0, "litres": 1000.0,
    "floz": 29.5735, "oz": 29.5735,
}


def parse_volume_ml(text: str | None) -> float | None:
    if not text:
        return None
    m = _VOLUME_RE.search(text)
    if not m:
        return None
    unit = re.sub(r"[.\s]", "", m.group(2).lower())
    return float(m.group(1)) * _UNIT_TO_ML.get(unit, 0.0) or None


def _validate_net_contents(declared, value, confidence):
    field = "net_contents"
    if value is None:
        if confidence >= HIGH_CONFIDENCE:
            return _result(field, declared, None, confidence, FAIL,
                           "Net contents were not found on the label.")
        return _result(field, declared, None, confidence, WARN,
                       "The AI could not confidently read the net contents. An agent should check the image.")
    if confidence < CONFIDENCE_WARN_THRESHOLD:
        return _result(field, declared, value, confidence, WARN,
                       "The AI was not confident reading the net contents. An agent should check the label image.")
    declared_ml = parse_volume_ml(declared)
    extracted_ml = parse_volume_ml(value)
    if declared_ml is not None and extracted_ml is not None:
        if abs(declared_ml - extracted_ml) < 1.0:
            return _result(field, declared, value, confidence, PASS,
                           "Net contents match the application.")
        return _result(field, declared, value, confidence, FAIL,
                       f"Net contents differ: label shows {value}, application declares {declared}.")
    # Fallback: normalized string equality (lowercase, no whitespace)
    if re.sub(r"\s+", "", declared.lower()) == re.sub(r"\s+", "", value.lower()):
        return _result(field, declared, value, confidence, PASS,
                       "Net contents match the application.")
    return _result(field, declared, value, confidence, FAIL,
                   f"Net contents differ: label shows {value}, application declares {declared}.")


def _validate_country(declared, value, confidence):
    field = "country_of_origin"
    declared_empty = not (declared or "").strip()
    if declared_empty and value is None:
        return _result(field, declared, None, confidence, PASS,
                       "No country of origin declared and none found on the label.")
    if declared_empty and value is not None:
        if confidence < HIGH_CONFIDENCE:
            return _result(field, declared, value, confidence, WARN,
                           "The label may show a country of origin but none was declared. An agent should check the image.")
        return _result(field, declared, value, confidence, FAIL,
                       f"The label shows a country of origin ('{value}') but none was declared in the application.")
    return _matrix_field(field, declared, value, confidence)


def _validate_government_warning(value, confidence, notes):
    field = "government_warning"
    declared = GOVERNMENT_WARNING_REQUIRED
    if value is None:
        return _result(field, declared, None, confidence, FAIL,
                       "The government warning was not found on the label.")
    if confidence < WARNING_CONFIDENCE_THRESHOLD:
        return _result(field, declared, value, confidence, WARN,
                       "Warning text partially unreadable. An agent should check the label image.")
    # Formatting checks from the AI's notes apply regardless of text match.
    notes_l = (notes or "").lower()
    if "title case" in notes_l or "not all caps" in notes_l:
        return _result(field, declared, value, confidence, FAIL,
                       "GOVERNMENT WARNING: must be in all caps.")
    if "not bold" in notes_l:
        return _result(field, declared, value, confidence, FAIL,
                       "GOVERNMENT WARNING: must be bold.")
    if "small font" in notes_l or "smaller font" in notes_l:
        return _result(field, declared, value, confidence, FAIL,
                       "Warning text font size appears smaller than surrounding text.")
    if _norm(value) == _norm(declared):
        return _result(field, declared, value, confidence, PASS,
                       "Government warning matches the required wording exactly.")
    return _result(field, declared, value, confidence, FAIL,
                   "Warning text does not match required wording.")


def validate(application_data: dict, extraction: dict) -> tuple[str, list[dict]]:
    """Compare declared fields against extraction. Returns (overall, results)."""
    results = []
    for field in ALL_APPLICATION_FIELDS:
        declared = application_data.get(field) or ""
        value, confidence, _notes = _get_extracted(extraction, field)
        if field == "alcohol_content":
            results.append(_validate_alcohol(declared, value, confidence))
        elif field == "net_contents":
            results.append(_validate_net_contents(declared, value, confidence))
        elif field == "country_of_origin":
            results.append(_validate_country(declared, value, confidence))
        else:
            results.append(_matrix_field(field, declared, value, confidence))

    gw_value, gw_confidence, gw_notes = _get_extracted(extraction, "government_warning")
    results.append(_validate_government_warning(gw_value, gw_confidence, gw_notes))

    return overall_status(results), results


def overall_status(results: list[dict]) -> str:
    statuses = {r["status"] for r in results}
    if FAIL in statuses:
        return FAIL
    if WARN in statuses:
        return WARN
    return PASS


def all_warn_results(application_data: dict, reason: str) -> tuple[str, list[dict]]:
    """Used when Claude returns malformed JSON: every field is WARN with
    confidence 0 and the application routes to the agent queue."""
    results = []
    for field in VALIDATED_FIELDS:
        declared = (GOVERNMENT_WARNING_REQUIRED if field == "government_warning"
                    else application_data.get(field) or "")
        results.append(_result(field, declared, None, 0.0, WARN, reason))
    return WARN, results
