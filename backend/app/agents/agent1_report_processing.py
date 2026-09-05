"""
Agent 1 -- Report Processing Agent

Responsibilities (per project spec):
  - Accept blood report (PDF/Image/DOCX)
  - Perform OCR
  - Extract blood parameters, read tables, detect report format
  - Correct OCR errors, validate units, normalize parameter names
  - Handle missing values

Output: clean, structured blood report (ExtractedReport)
"""
from app.models import PipelineState, ExtractedReport, BloodParameter
from app.ocr_extraction import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
    parse_parameters_from_text,
)
from app.reference_ranges import normalize_parameter_name, classify_value


def _detect_format(text: str) -> str:
    lower = text.lower()
    if "cbc" in lower or "complete blood count" in lower:
        return "CBC (Complete Blood Count) panel"
    if "lipid" in lower:
        return "Lipid profile"
    if "thyroid" in lower or "tsh" in lower:
        return "Thyroid panel"
    if "liver" in lower or "sgpt" in lower or "sgot" in lower:
        return "Liver function test"
    if "kidney" in lower or "creatinine" in lower:
        return "Kidney function test"
    return "General blood panel"


def run(state: PipelineState) -> PipelineState:
    warnings = []
    raw_bytes = state.raw_text.encode("utf-8", errors="ignore") if state.file_type == "text" else None

    text = state.raw_text
    confidence = 1.0

    # If raw bytes were supplied via API (file upload path), the caller
    # already decoded them into state.raw_text using the helpers below
    # in main.py — this function operates purely on text at this point.

    if not text or not text.strip():
        warnings.append("No text could be extracted from the uploaded report.")
        state.extracted = ExtractedReport(parameters=[], report_format_detected=None,
                                           ocr_confidence=0.0, warnings=warnings)
        return state

    raw_params = parse_parameters_from_text(text)
    if not raw_params:
        warnings.append("Could not confidently detect a tabular parameter layout; "
                         "results may be incomplete. Try a clearer scan.")

    structured: list[BloodParameter] = []
    seen = set()
    for p in raw_params:
        canonical = normalize_parameter_name(p["name"])
        display_name = canonical.title() if canonical else p["name"].title()
        key = canonical or display_name.lower()
        if key in seen:
            continue
        seen.add(key)

        status = "unknown"
        if canonical:
            status = classify_value(canonical, p["value"])
        structured.append(BloodParameter(
            name=display_name,
            value=p["value"],
            raw_value=p["raw_value"],
            unit=p["unit"] or None,
            reference_range=p["reference_range"] or None,
            status=status,
        ))

    if not structured:
        warnings.append("Zero parameters extracted — check that the file is a valid blood report.")

    state.extracted = ExtractedReport(
        parameters=structured,
        report_format_detected=_detect_format(text),
        ocr_confidence=confidence,
        warnings=warnings,
    )
    return state
