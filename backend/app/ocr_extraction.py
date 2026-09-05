"""
Report Ingestion + OCR & Extraction Layer.

Supports:
  - Native-text PDFs      -> pdfplumber
  - Scanned PDFs / images -> pytesseract OCR (falls back gracefully if
                              tesseract binary isn't installed on the host)
  - DOCX                  -> python-docx

All paths converge to plain text, which Agent 1 then parses into
structured BloodParameter rows using regex + fuzzy unit detection.
"""
import io
import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

# A line like: "Hemoglobin   13.2   g/dL   13.0-17.0"
PARAM_LINE_RE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9 /()\-\.]{1,40}?)\s*[:\-]?\s*"
    r"(?P<value>\d+\.?\d*)\s*"
    r"(?P<unit>[A-Za-z/%\^0-9µu]{1,15})?\s*"
    r"(?P<range>\(?\d+\.?\d*\s*-\s*\d+\.?\d*\)?)?"
)


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, float]:
    """Returns (text, confidence). Tries native text first, then OCR."""
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(pages)
    except Exception as e:  # noqa: BLE001
        logger.warning("pdfplumber failed: %s", e)

    if text.strip():
        return text, 0.98  # native text extraction is effectively exact

    # Scanned PDF -> rasterize + OCR
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        images = convert_from_bytes(file_bytes)
        ocr_text = []
        confidences = []
        for img in images:
            ocr_text.append(pytesseract.image_to_string(img))
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            confs = [int(c) for c in data.get("conf", []) if c not in ("-1", -1)]
            if confs:
                confidences.append(sum(confs) / len(confs))
        avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.5
        return "\n".join(ocr_text), avg_conf
    except Exception as e:  # noqa: BLE001
        logger.warning("OCR fallback failed: %s", e)
        return "", 0.0


def extract_text_from_image(file_bytes: bytes) -> Tuple[str, float]:
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confs = [int(c) for c in data.get("conf", []) if c not in ("-1", -1)]
        conf = (sum(confs) / len(confs) / 100.0) if confs else 0.5
        return text, conf
    except Exception as e:  # noqa: BLE001
        logger.warning("Image OCR failed: %s", e)
        return "", 0.0


def extract_text_from_docx(file_bytes: bytes) -> Tuple[str, float]:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" ".join(cell.text for cell in row.cells))
        return "\n".join(parts), 0.98
    except Exception as e:  # noqa: BLE001
        logger.warning("docx extraction failed: %s", e)
        return "", 0.0


NON_PARAMETER_LINE_PATTERNS = re.compile(
    r"(patient\s*id|report\s*format|sample\s*id|lab(oratory)?\s*(name|report)|"
    r"date\s*of|collected|reported|physician|doctor|address|phone|"
    r"page\s*\d|diagnostic|pathology|medical\s*centre|medical\s*center)",
    re.IGNORECASE,
)


def parse_parameters_from_text(text: str) -> List[dict]:
    """Regex-based structured parsing used by the rule-based fallback path
    and as a safety net whenever the LLM extraction returns nothing."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 4:
            continue
        if NON_PARAMETER_LINE_PATTERNS.search(line):
            continue
        match = PARAM_LINE_RE.search(line)
        if not match:
            continue
        name = match.group("name").strip(" .:-")
        value = match.group("value")
        if not name or not value:
            continue
        try:
            value_f = float(value)
        except ValueError:
            continue
        results.append({
            "name": name,
            "value": value_f,
            "raw_value": value,
            "unit": (match.group("unit") or "").strip(),
            "reference_range": (match.group("range") or "").strip("() "),
        })
    return results
