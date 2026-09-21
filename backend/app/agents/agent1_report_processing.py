"""
Agent 1 -- Report Processing Agent

Responsibilities (per project spec):
  - Accept blood report (PDF/Image/DOCX)
  - Perform OCR
  - Extract blood parameters, read tables, detect report format
  - Correct OCR errors, validate units, normalize parameter names
  - Handle missing values

Output: clean, structured blood report (ExtractedReport)

Accuracy design (real-world reports):
  * The reference range PRINTED on the report is used for classification
    whenever it can be read (labs differ by sex/age/method). The built-in
    table is only a fallback.
  * Units are normalised (cells/cumm -> 10^3/uL, lakhs -> 10^3/uL, mmol/L ->
    mg/dL ...) before values are reported / compared with the table.
  * Unknown parameter names are never force-matched to a known one.
"""
from app.models import PipelineState, ExtractedReport, BloodParameter
from app.ocr_extraction import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
    parse_parameters_from_text,
)
from app.reference_ranges import (
    normalize_parameter_name,
    display_name,
    get_reference,
    classify_value,
    classify_with_range,
    convert_to_standard,
)


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


def _fmt(x) -> str:
    return f"{x:.4g}"


def build_parameter(p: dict, warnings: list):
    """raw parsed row -> (canonical_or_None, BloodParameter)."""
    canonical = normalize_parameter_name(p["name"])
    value, unit = p["value"], p["unit"] or None
    lo, hi = p.get("ref_low"), p.get("ref_high")
    has_printed = lo is not None or hi is not None

    # 1) status: printed range first (same units as the printed value) ...
    status = "unknown"
    if has_printed:
        status = classify_with_range(value, lo, hi)

    out_value, out_unit = value, unit
    out_lo, out_hi = lo, hi
    name = display_name(canonical) if canonical else p["name"].strip()

    if canonical:
        fn, std_unit, state = convert_to_standard(canonical, unit)
        if state == "no_unit" and canonical in ("wbc count", "platelet count") and value >= 1000:
            # count printed per cumm without a unit column (e.g. 11200) -> 10^3/uL
            fn, state = (lambda v: v / 1000), "converted"
            unit = "/cumm"
        if state == "unknown_unit":
            warnings.append(f"{name}: unit '{unit}' is not recognised for this test; "
                            f"{'used the range printed on the report' if has_printed else 'status left unknown'}.")
        else:
            out_value = round(fn(value), 4)
            out_unit = std_unit
            out_lo = None if lo is None else round(fn(lo), 4)
            out_hi = None if hi is None else round(fn(hi), 4)
            if state == "converted":
                warnings.append(f"{name}: converted {p['raw_value']} {unit} -> {_fmt(out_value)} {std_unit}.")
            # 2) ... else fall back to the built-in table (in table units)
            if not has_printed:
                status = classify_value(canonical, out_value)
                ref = get_reference(canonical)
                out_lo, out_hi = ref["low"], ref["high"]

    if out_lo is not None and out_hi is not None:
        ref_str = f"{_fmt(out_lo)}-{_fmt(out_hi)}"
    elif out_hi is not None:
        ref_str = f"<{_fmt(out_hi)}"
    elif out_lo is not None:
        ref_str = f">{_fmt(out_lo)}"
    else:
        ref_str = None

    return canonical, BloodParameter(
        name=name,
        value=out_value,
        raw_value=p["raw_value"],
        unit=out_unit,
        reference_range=ref_str,
        status=status,
    )


def run(state: PipelineState) -> PipelineState:
    warnings = []
    text = state.raw_text
    confidence = state.ocr_confidence

    # If raw bytes were supplied via API (file upload path), the caller
    # already decoded them into state.raw_text using the helpers in
    # main.py -- this function operates purely on text at this point.
    if not text or not text.strip():
        warnings.append("No text could be extracted from the uploaded report.")
        state.extracted = ExtractedReport(parameters=[], report_format_detected=None,
                                          ocr_confidence=0.0, warnings=warnings)
        return state

    if confidence < 0.85:
        warnings.append(f"Low OCR confidence ({confidence:.0%}). Please verify every extracted value "
                        "against the original report before relying on the analysis.")

    raw_params = parse_parameters_from_text(text)
    if not raw_params:
        warnings.append("Could not confidently detect a tabular parameter layout; "
                        "results may be incomplete. Try a clearer scan.")

    structured: list[BloodParameter] = []
    seen = set()
    for p in raw_params:
        canonical, param = build_parameter(p, warnings)
        key = canonical or param.name.lower()
        if key in seen:
            continue
        seen.add(key)
        structured.append(param)

    if not structured:
        warnings.append("Zero parameters extracted — check that the file is a valid blood report.")

    state.extracted = ExtractedReport(
        parameters=structured,
        report_format_detected=_detect_format(text),
        ocr_confidence=confidence,
        warnings=warnings,
    )
    return state
