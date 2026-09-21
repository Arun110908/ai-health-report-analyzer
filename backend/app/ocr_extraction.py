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

from app.reference_ranges import normalize_parameter_name, is_exact_alias as _clean_alias_hit


def _prep_for_ocr(img):
    """Grayscale + autocontrast + upscale small scans. Tesseract is far more
    accurate on ~300 DPI, high-contrast text than on raw phone photos."""
    from PIL import Image, ImageOps
    img = ImageOps.autocontrast(ImageOps.grayscale(img))
    if img.width < 1800:
        scale = 1800 / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    return img


OCR_CONFIG = "--psm 6"  # assume one uniform block of text (lab tables)


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
            img = _prep_for_ocr(img)
            ocr_text.append(pytesseract.image_to_string(img, config=OCR_CONFIG))
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
        img = _prep_for_ocr(Image.open(io.BytesIO(file_bytes)))
        text = pytesseract.image_to_string(img, config=OCR_CONFIG)
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
    r"(patient|report\s*format|sample|specimen|lab(oratory)?\s*(name|report|no|reg)|"
    r"date|collected|reported|received|physician|doctor|dr\.|address|phone|mobile|"
    r"contact|page\s*\d|diagnostic|pathology|medical\s*cent|ref(erred)?\.?\s*by|"
    r"reg(istration)?\.?\s*no|barcode|accession|visit|invoice|bill|www\.|@|"
    r"method\s*:|interpretation|note\s*:|end of report)",
    re.IGNORECASE,
)

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
# a number that stands alone (not glued to letters like HbA1c / B12 / 10^3)
STANDALONE_NUM_RE = re.compile(rf"(?<![A-Za-z0-9.,^*\-])({_NUM})(?![0-9^*])")
RANGE_RE = re.compile(rf"(?<![0-9.])({_NUM})\s*(?:-|\u2013|\u2014|to)\s*({_NUM})(?![0-9])", re.IGNORECASE)
UPPER_RE = re.compile(rf"(?:<|\u2264|up\s*to|upto|less\s*than)\s*=?\s*({_NUM})", re.IGNORECASE)
LOWER_RE = re.compile(rf"(?:>|\u2265|more\s*than|greater\s*than)\s*=?\s*({_NUM})", re.IGNORECASE)
UNIT_RE = re.compile(r"^(?:x?10[\^*]\d+/?)?/?[A-Za-z\u00b5\u03bc][A-Za-z0-9\u00b5\u03bc/^*\u00b3.%-]*$|^%$")
FLAG_TOKENS = {"h", "l", "hh", "ll", "high", "low", "normal", "abnormal", "*", "h*", "l*",
               "\u2191", "\u2193", "(h)", "(l)", "critical", "borderline", "optimal", "desirable"}
NOT_UNIT_PREFIXES = ("ref", "normal", "range", "method", "bio", "interval", "level", "desirable",
                     "optimal", "borderline", "high", "low", "near", "male", "female", "adult",
                     "children", "child", "men", "women", "m:", "f:")


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def _plausible_name(name: str) -> bool:
    """A known parameter name, and not a name glued to the previous column's
    numbers ('Hemoglobin (Hb)  15.5  g/dL  13 -' must not count as a name).
    Numbers are only allowed when the whole string is a known alias
    ('Vitamin D, 25 Hydroxy')."""
    if not normalize_parameter_name(name):
        return False
    if STANDALONE_NUM_RE.search(name):
        return _clean_alias_hit(name)
    return True


def _split_name_value(line: str):
    """Find (name, value_match). Alias-guided: prefer the split whose left-hand
    side is a KNOWN parameter, so 'Vitamin D, 25 Hydroxy 32.4 ng/mL' or
    'HbA1c 5.4 %' are not cut at the wrong number."""
    cands = list(STANDALONE_NUM_RE.finditer(line))
    best = (None, None)
    for m in cands[:4]:  # longest left-hand side that is a KNOWN parameter wins
        name = re.sub(r"^\d+[.)]?\s+", "", line[:m.start()].strip(" \t:|-\u2013\u2014.,*"))
        if name and _plausible_name(name):
            best = (name, m)
    if best[0]:
        return best
    for m in cands[:2]:  # unknown parameter: first number after some alphabetic text
        name = re.sub(r"^\d+[.)]?\s+", "", line[:m.start()].strip(" \t:|-\u2013\u2014.,*"))
        if name and re.search(r"[A-Za-z]{2}", name):
            return name, m
    return None, None


def parse_parameters_from_text(text: str) -> List[dict]:
    """Structured parsing of report text -> raw parameter rows.

    Handles: 'Name: 13.2 g/dL (13.0-17.0)', spaced/tab/pipe tables, H/L flag
    columns, thousands separators (6,500), one-sided ranges (<200, >40),
    sex-specific or multi-band ranges (ignored -> table fallback), numbered rows.

    Each row: name, value, raw_value, unit, ref_low, ref_high, reference_range, flag
    """
    results = []
    for line in text.splitlines():
        line = line.replace("|", "  ").replace("\t", "  ").strip()
        if len(line) < 4 or NON_PARAMETER_LINE_PATTERNS.search(line):
            continue
        name, m = _split_name_value(line)
        if not name:
            continue
        raw_value = m.group(1)
        try:
            value = _to_float(raw_value)
        except ValueError:
            continue
        rest = line[m.end():]

        # ---- reference range printed on the report ----
        bands = RANGE_RE.findall(rest), UPPER_RE.findall(rest), LOWER_RE.findall(rest)
        n_bands = sum(len(b) for b in bands)
        ref_low = ref_high = None
        if n_bands == 1:  # exactly one band -> unambiguous
            if bands[0]:
                ref_low, ref_high = _to_float(bands[0][0][0]), _to_float(bands[0][0][1])
                if ref_high < ref_low:
                    ref_low = ref_high = None
            elif bands[1]:
                ref_high = _to_float(bands[1][0])
            else:
                ref_low = _to_float(bands[2][0])
        # n_bands >= 2 (male/female, desirable/borderline/high ...) -> ambiguous, ignore

        # ---- unit + flag ----
        unit, flag = "", ""
        for tok in rest.split():
            t = tok.strip("(),;:")
            tl = t.lower()
            if not t:
                continue
            if tl in FLAG_TOKENS:
                flag = flag or tl
                continue
            if unit:
                continue
            if tl.startswith(NOT_UNIT_PREFIXES) or not UNIT_RE.match(t):
                if RANGE_RE.match(t) or t[:1] in "<>":
                    unit = unit or ""  # range started before any unit: no unit printed
                continue
            unit = t

        if ref_low is not None and ref_high is not None:
            ref_str = f"{ref_low:g}-{ref_high:g}"
        elif ref_high is not None:
            ref_str = f"<{ref_high:g}"
        elif ref_low is not None:
            ref_str = f">{ref_low:g}"
        else:
            ref_str = ""

        known = normalize_parameter_name(name) is not None
        # Unknown names are only kept if the row really looks like a lab
        # result (has a unit AND a printed range) -> drops 'Age: 34 Years' etc.
        if not known and not (unit and (ref_low is not None or ref_high is not None)):
            continue

        results.append({
            "name": name, "value": value, "raw_value": raw_value, "unit": unit,
            "ref_low": ref_low, "ref_high": ref_high, "reference_range": ref_str, "flag": flag,
        })
    return results
