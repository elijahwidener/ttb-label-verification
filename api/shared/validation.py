"""The validation engine — the core decision layer.

Claude extracts (OCR); this module compares each extracted value against what
the submitter declared and produces an auditable PASS/WARN/FAIL per field with
a plain-language reason. Thresholds are best-guesses from stakeholder
interviews and need empirical tuning (see docs/validation.md)."""

import re

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from .models import ALL_APPLICATION_FIELDS, FIELD_LABELS, VALIDATED_FIELDS

GOVERNMENT_WARNING_REQUIRED = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

# Text fields PASS only on an exact match after style normalization (see
# normalize_for_match). Fuzzy scoring on the normalized strings then separates
# WARN (≥60: real but small difference — typo or possibly different entity,
# human judgment) from FAIL (<60: confident mismatch).
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


# Two-axis model: the AI's `confidence` says how sure we are we READ the label
# right; the match step then asks whether the (trusted) text MEANS the same as
# what was declared. Matching must be strict on spelling/content but forgiving
# on *style* — case, punctuation, &/and, corporate suffixes (Inc/Incorporated),
# street abbreviations (St/Street). So we normalize style away explicitly, then
# require an EXACT match for PASS. A real textual difference that survives
# normalization (e.g. "Wnery" vs "Winery" — a typo, or a different entity) is
# NOT auto-passed; fuzzy scoring only separates WARN from FAIL after that.

# Each variant maps to one canonical token (whole-token replacement only).
_CANON = {
    "incorporated": "inc", "inc": "inc",
    "corporation": "corp", "corp": "corp",
    "company": "co", "co": "co",
    "limited": "ltd", "ltd": "ltd",
    "llc": "llc", "lp": "lp", "plc": "plc",
    "street": "st", "st": "st",
    "avenue": "ave", "ave": "ave", "av": "ave",
    "road": "rd", "rd": "rd",
    "boulevard": "blvd", "blvd": "blvd",
    "drive": "dr", "dr": "dr",
    "lane": "ln", "ln": "ln",
    "court": "ct", "ct": "ct",
    "place": "pl", "pl": "pl",
    "highway": "hwy", "hwy": "hwy",
    "parkway": "pkwy", "pkwy": "pkwy",
    "square": "sq", "sq": "sq",
    "suite": "ste", "ste": "ste",
    "apartment": "apt", "apt": "apt",
    "north": "n", "south": "s", "east": "e", "west": "w",
    "saint": "st",
}


def normalize_for_match(text: str | None) -> str:
    """Strip *style* so that what's left is content. Lowercase; &→and; drop
    apostrophes/periods/commas/quotes with no gap (L.L.C.→llc, Stone's→stones);
    other separators → space; canonicalize corporate + street tokens."""
    t = (text or "").casefold()
    t = t.replace("&", " and ")
    t = re.sub(r"[.,'’\"]", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(_CANON.get(tok, tok) for tok in t.split())


def _is_typo_pair(a: str, b: str) -> bool:
    """True when two differing tokens look like a misspelling of the SAME word
    (vs. two genuinely different words). Heuristics: both ≥4 chars (short tokens
    are too ambiguous to auto-reject), same first letter (typos rarely change
    it; different words usually start differently), edit distance ≤ 2."""
    if len(a) < 4 or len(b) < 4 or a[0] != b[0]:
        return False
    return Levenshtein.distance(a, b) <= 2


def _is_pure_typo(nd: str, nv: str) -> bool:
    """The two normalized strings are the same words except one or more are
    misspelled — no words added, dropped, or swapped for different words."""
    dt, vt = nd.split(), nv.split()
    if len(dt) != len(vt):
        return False  # a whole word added/removed -> structural, not a typo
    diffs = [(d, v) for d, v in zip(dt, vt) if d != v]
    return bool(diffs) and all(_is_typo_pair(d, v) for d, v in diffs)


def _raw_fuzzy(a: str, b: str, token_set: bool = False) -> float:
    score = max(fuzz.ratio(a, b), fuzz.token_sort_ratio(a, b))
    if token_set:
        score = max(score, fuzz.token_set_ratio(a, b))
    return score


def fuzzy_score(declared: str, extracted: str, token_set: bool = False) -> float:
    """Style-insensitive similarity over normalized strings."""
    return _raw_fuzzy(normalize_for_match(declared), normalize_for_match(extracted), token_set)


# Real labels almost always qualify the producer ("Bottled by X", "Distilled
# and bottled by X"). The declared producer name rarely includes that phrase,
# so strip standard qualifiers before comparing — otherwise nearly every
# application WARNs on producer_name. The agent still sees the original
# transcription in field_results.
_PRODUCER_PREFIX_RE = re.compile(
    r"^(?:(?:distilled|produced|bottled|brewed|made|crafted|imported|vinted|cellared|blended)"
    r"(?:\s*(?:,|and|&)\s*(?:distilled|produced|bottled|brewed|made|crafted|imported|vinted|cellared|blended))*"
    r"\s+by[:\s]+)",
    re.IGNORECASE,
)


def strip_producer_qualifier(text: str | None) -> str | None:
    if not text:
        return text
    stripped = _PRODUCER_PREFIX_RE.sub("", text).strip()
    return stripped or text


def _is_acronym(short: str, long: str) -> bool:
    """True when `short` is the initials of multi-word `long` (IPA / India Pale Ale)."""
    s = re.sub(r"[^a-z]", "", (short or "").casefold())
    words = re.findall(r"[a-z]+", (long or "").casefold())
    return len(words) >= 2 and len(s) == len(words) and s == "".join(w[0] for w in words)


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


def _matrix_field(field, declared, value, confidence, compare_declared=None,
                  compare_value=None, token_set=False):
    """Decision matrix (§11.1) for fuzzy-matched fields. compare_* override the
    strings used for scoring while declared/value stay in the result row."""
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
    nd = normalize_for_match(compare_declared if compare_declared is not None else declared)
    nv = normalize_for_match(compare_value if compare_value is not None else value)
    # PASS only when identical once style is stripped — so punctuation/casing/
    # suffix differences pass, but a real spelling or wording difference does not.
    if nd == nv:
        return _result(field, declared, value, confidence, PASS,
                       f"{label} matches the application.")
    # Same words, different order — still the same thing.
    if sorted(nd.split()) == sorted(nv.split()):
        return _result(field, declared, value, confidence, PASS,
                       f"{label} matches the application.")
    # class_type only: a declared class fully contained in the label's more
    # specific designation ("Whiskey" ⊂ "Kentucky Straight Bourbon Whiskey").
    if token_set and fuzz.token_set_ratio(nd, nv) >= 100:
        return _result(field, declared, value, confidence, PASS,
                       f"{label} matches the application (the label is more specific).")
    # Clear misspelling of the same words: a human can't approve a mismatched
    # spelling in an official record, so don't queue it — kick it back to the
    # submitter to correct. (class_type FAILs are demoted to WARN by the caller.)
    if _is_pure_typo(nd, nv):
        return _result(field, declared, value, confidence, FAIL,
                       f"{label} does not match the label: the application says '{declared}' but "
                       f"the label reads '{value}', which looks like a spelling difference. "
                       f"Please correct the application and resubmit.")
    score = _raw_fuzzy(nd, nv, token_set=token_set)
    if score >= FUZZY_FAIL_THRESHOLD:
        return _result(field, declared, value, confidence, WARN,
                       f"{label} on the label differs from the application beyond formatting "
                       f"(similarity {int(score)}/100) — for example an extra word, an abbreviation, "
                       f"or different wording. An agent should confirm they describe the same thing.")
    return _result(field, declared, value, confidence, FAIL,
                   f"{label} on the label does not match the application (similarity {int(score)}/100).")


_ABV_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def parse_abv(text: str | None) -> float | None:
    if not text:
        return None
    m = _ABV_RE.search(text)
    if m:
        return float(m.group(1))
    # Bare number ("45", "13.5") — the form asks for just the percentage.
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", text)
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
    norm_extracted = _norm(value)
    # The statute requires capitals for "GOVERNMENT WARNING:" specifically; the
    # body has no case requirement (labels often print the whole warning in
    # caps — that's compliant). So: prefix must be literally capitalized,
    # wording is compared case-insensitively.
    if (norm_extracted.casefold().startswith("government warning")
            and not norm_extracted.startswith("GOVERNMENT WARNING")):
        return _result(field, declared, value, confidence, FAIL,
                       "GOVERNMENT WARNING: must be in all caps.")
    if norm_extracted.casefold() == _norm(declared).casefold():
        return _result(field, declared, value, confidence, PASS,
                       "Government warning matches the required wording.")
    return _result(field, declared, value, confidence, FAIL,
                   "Warning text does not match required wording.")


def validate(application_data: dict, extraction: dict) -> tuple[str, list[dict]]:
    """Compare declared fields against extraction. Returns (overall, results)."""
    results = []
    for field in ALL_APPLICATION_FIELDS:
        declared = application_data.get(field) or ""
        value, confidence, _notes = _get_extracted(extraction, field)
        if field == "class_type":
            r = _matrix_field(field, declared, value, confidence, token_set=True)
            # Class/type never auto-rejects: beverage-type taxonomy is out of
            # scope (a generic declared class like "Wine" against a specific
            # label "Cabernet Sauvignon" has no lexical overlap, and "IPA" vs
            # "India Pale Ale" is an abbreviation). Without a taxonomy the
            # system can't safely call a class mismatch wrong — so any non-match
            # is WARN for a human, not FAIL.
            if r["status"] == FAIL and value:
                if _is_acronym(declared, value) or _is_acronym(value, declared):
                    reason = ("Class / type on the label looks like an abbreviation of the "
                              "declared class. An agent should confirm they mean the same thing.")
                else:
                    reason = ("Class / type on the label does not obviously match the declared "
                              "class. The system does not model beverage-type relationships, so "
                              "an agent should confirm whether they describe the same product.")
                r = _result(field, declared, value, confidence, WARN, reason)
            results.append(r)
        elif field == "alcohol_content":
            results.append(_validate_alcohol(declared, value, confidence))
        elif field == "net_contents":
            results.append(_validate_net_contents(declared, value, confidence))
        elif field == "country_of_origin":
            results.append(_validate_country(declared, value, confidence))
        elif field == "producer_name":
            results.append(_matrix_field(
                field, declared, value, confidence,
                compare_declared=strip_producer_qualifier(declared),
                compare_value=strip_producer_qualifier(value),
            ))
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
