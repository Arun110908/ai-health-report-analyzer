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
    """Prepare phone photos and scans for table-oriented OCR.

    EXIF rotation is corrected first.  The image is then made grayscale,
    contrast-normalised, enlarged to roughly 300-DPI text size, and lightly
    sharpened.  This intentionally avoids aggressive thresholding: hard
    black/white conversion can erase decimal points and faint lab-table lines.
    """
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    img = ImageOps.exif_transpose(img)
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img, cutoff=1)
    if img.width < 2200:
        scale = 2200 / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.35)
    return img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=145, threshold=3))


OCR_CONFIG = "--oem 3 --psm 6 -c preserve_interword_spaces=1"


def _mean_ocr_confidence(data: dict) -> float:
    """Convert Tesseract's confidence strings to a reliable 0..1 score."""
    values = []
    for raw in data.get("conf", []):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            values.append(value)
    return (sum(values) / len(values) / 100.0) if values else 0.5


def _readable_native_text(text: str) -> bool:
    """Avoid accepting sparse/gibberish PDF text instead of running OCR."""
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 80:
        return False
    alphanumeric = sum(ch.isalnum() for ch in compact)
    return alphanumeric / max(len(compact), 1) >= 0.45


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

    if _readable_native_text(text):
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
            confidences.append(_mean_ocr_confidence(data) * 100)
        avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.5
        return "\n".join(ocr_text), avg_conf
    except Exception as e:  # noqa: BLE001
        logger.warning("OCR fallback failed: %s", e)
        return "", 0.0


# Blurry phone photos respond very differently to different Tesseract page-
# segmentation modes -- there is no single PSM that wins on every photo.
# We run a small, cheap "best-of-N" race and keep whichever result looks
# most like an actual lab report, rather than trusting one fixed config.
_OCR_PSM_CANDIDATES = [
    "--oem 3 --psm 6 -c preserve_interword_spaces=1",   # uniform block (default: clean scans)
    "--oem 3 --psm 11 -c preserve_interword_spaces=1",  # sparse text, no fixed layout (very blurry / low-res)
]
# Kept to 2 candidates on purpose: each extra config roughly doubles the
# per-image OCR time, which matters on a free-tier web request. If you have
# CPU/time budget to spare, add "--oem 3 --psm 4 -c preserve_interword_spaces=1"
# (single variable-sized column -- helps on skewed/rotated table photos) back
# to this list; evaluate_ocr.py measures the trade-off directly.


def _score_ocr_text(text: str) -> int:
    """How usable is this OCR text? Counts rows that plausibly parsed into
    a real lab parameter -- a far better signal for a blurry photo than raw
    Tesseract confidence, which stays low even on a perfectly legible scan."""
    if not text.strip():
        return 0
    try:
        return len(parse_parameters_from_text(text))
    except Exception:  # noqa: BLE001
        return 0


def extract_text_from_image(file_bytes: bytes) -> Tuple[str, float]:
    try:
        from PIL import Image
        import pytesseract
        img = _prep_for_ocr(Image.open(io.BytesIO(file_bytes)))
        best_text, best_conf, best_score = "", 0.0, -1
        for config in _OCR_PSM_CANDIDATES:
            try:
                text = pytesseract.image_to_string(img, config=config)
                score = _score_ocr_text(text)
            except Exception:  # noqa: BLE001
                continue
            if score > best_score:
                data = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)
                best_text, best_conf, best_score = text, _mean_ocr_confidence(data), score
        return best_text, best_conf
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
    r"method\s*:|interpretation|note\s*:|end of report|\b(?:is|are)\s+defined\s+as\b)",
    re.IGNORECASE,
)

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
# a number that stands alone (not glued to letters like HbA1c / B12 / 10^3)
STANDALONE_NUM_RE = re.compile(rf"(?<![A-Za-z0-9.,^*\-])({_NUM})(?![0-9^*])")
# Native PDF text often glues an H/L flag to a result (for example H10570).
# Standalone-number matching cannot see that value because it follows a letter.
FLAGGED_NUM_RE = re.compile(
    rf"(?<![A-Za-z0-9.,^*\-])(?P<flag>H|L)\s*(?P<value>{_NUM})(?![0-9^*])",
    re.IGNORECASE,
)
RANGE_RE = re.compile(rf"(?<![0-9.])({_NUM})\s*(?:-|\u2013|\u2014|to)\s*({_NUM})(?![0-9])", re.IGNORECASE)
UPPER_RE = re.compile(rf"(?:<|\u2264|up\s*to|upto|less\s*than)\s*=?\s*({_NUM})", re.IGNORECASE)
LOWER_RE = re.compile(rf"(?:>|\u2265|more\s*than|greater\s*than)\s*=?\s*({_NUM})", re.IGNORECASE)
UNIT_RE = re.compile(r"^(?:x?10[\^*]\d+/?)?/?[A-Za-z\u00b5\u03bc][A-Za-z0-9\u00b5\u03bc/^*\u00b3.%-]*$|^%$")
FLAG_TOKENS = {"h", "l", "hh", "ll", "high", "low", "normal", "abnormal", "*", "h*", "l*",
               "\u2191", "\u2193", "(h)", "(l)", "critical", "borderline", "optimal", "desirable"}
NOT_UNIT_PREFIXES = ("ref", "normal", "range", "method", "bio", "interval", "level", "desirable",
                     "optimal", "borderline", "high", "low", "near", "male", "female", "adult",
                     "children", "child", "men", "women", "m:", "f:", "up", "to", "non", "reactive")


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def _plausible_name(name: str) -> bool:
    """A known parameter name, and not a name glued to the previous column's
    numbers ('Hemoglobin (Hb)  15.5  g/dL  13 -' must not count as a name).
    Numbers are only allowed when the whole string is a known alias
    ('Vitamin D, 25 Hydroxy')."""
    # A real test name is short. This guard stops explanatory prose from
    # becoming a result merely because a parenthesized phrase resembles an
    # alias (for example a vitamin-D explanation that contains "vitamin D3").
    if len(re.findall(r"[A-Za-z]{2,}", name)) > 10:
        return False
    if not normalize_parameter_name(name):
        return False
    if STANDALONE_NUM_RE.search(name):
        return _clean_alias_hit(name)
    return True


def _number_from_match(match) -> str:
    """Return a numeric capture from either normal or flag-glued matches."""
    return match.group("value") if "value" in match.groupdict() else match.group(1)


def _clean_result_name(raw_name: str) -> tuple[str, str]:
    """Remove a result-column H/L marker without touching names such as HDL."""
    # A comparison sign can sit between a marker and its value, e.g.
    # ``Vitamin B12 L < 148``. Strip it before checking the final token.
    name = raw_name.strip(" \t:|-\u2013\u2014.,*<>=")
    marker = re.search(r"(?:^|\s)(H|L|HH|LL|HIGH|LOW)$", name, re.IGNORECASE)
    if not marker:
        return name, ""
    return name[:marker.start()].strip(" \t:|-\u2013\u2014.,*"), marker.group(1).lower()


def _split_name_value(line: str):
    """Find ``(name, value_match, flag)`` from one report row.

    The split is alias-guided: the longest known parameter on the left wins,
    preserving names such as ``Vitamin D, 25 Hydroxy`` and ``HbA1c``. It also
    accepts H/L markers glued to values in native PDF text extraction.
    """
    candidates = [(m, "") for m in STANDALONE_NUM_RE.finditer(line)]
    candidates.extend((m, m.group("flag").lower()) for m in FLAGGED_NUM_RE.finditer(line))
    candidates.sort(key=lambda item: item[0].start())

    parsed = []
    for match, glued_flag in candidates[:5]:
        raw_name = re.sub(r"^\d+[.)]?\s+", "", line[:match.start()])
        name, suffix_flag = _clean_result_name(raw_name)
        flag = glued_flag or suffix_flag
        if name:
            parsed.append((name, match, flag))

    best = (None, None, "")
    for name, match, flag in parsed:
        if _plausible_name(name):
            best = (name, match, flag)
    if best[0]:
        return best

    for name, match, flag in parsed[:2]:
        # Unknown names are retained only as a last resort. The caller still
        # requires a unit and a printed range before it accepts such a row.
        if len(re.findall(r"[A-Za-z]{2,}", name)) <= 10 and re.search(r"[A-Za-z]{2}", name):
            return name, match, flag
    return None, None, ""


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
        name, m, glued_flag = _split_name_value(line)
        if not name:
            continue
        raw_value = _number_from_match(m)
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
        unit, flag = "", glued_flag
        toks = rest.split()
        i = 0
        while i < len(toks):
            t = toks[i].strip("(),;:")
            tl = t.lower()
            i += 1
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
            # a bare magnitude word ('micro', 'milli') glued to its unit on
            # the NEXT token by a space in the source PDF ('micro g/dL')
            if tl in ("micro", "milli", "nano") and i < len(toks) and UNIT_RE.match(toks[i]):
                unit = t + toks[i]
                i += 1
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
