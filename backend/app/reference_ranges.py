"""
Medical Knowledge Layer (offline component of the RAG system).

This module ships a curated, source-cited reference-range table compiled
from publicly available WHO / NIH / Mayo Clinic guideline summaries.
It acts as:
  1. The grounding/context passed into the LLM prompts (retrieval step),
  2. A deterministic fallback so the app still works with zero LLM cost /
     no internet access (used by the rule-based fallback engine).

IMPORTANT (accuracy on real reports)
------------------------------------
Real labs print their OWN reference range next to every result, and those
ranges depend on sex / age / method (e.g. haemoglobin is 13-17 g/dL for men
but 12-15 g/dL for women). The table below is therefore only a FALLBACK:
Agent 1 classifies against the range printed on the report whenever one can
be read, and only uses this table when the report has no usable range.

Each entry: unit, low, high, source, aliases
"""
import re
import difflib
from typing import Dict, Optional, Callable, Tuple, List

# name (normalized, lowercase) -> reference info
REFERENCE_RANGES: Dict[str, Dict] = {
    # ---- Complete blood count ----
    "hemoglobin": {"unit": "g/dL", "low": 13.0, "high": 17.0, "source": "WHO / Mayo Clinic",
                   "aliases": ["hb", "hgb", "haemoglobin", "hemoglobin hb", "haemoglobin hb", "hb g dl"],
                   "display": "Hemoglobin"},
    "hematocrit": {"unit": "%", "low": 38.8, "high": 50.0, "source": "Mayo Clinic",
                   "aliases": ["hct", "pcv", "packed cell volume", "haematocrit", "hematocrit pcv"],
                   "display": "Hematocrit"},
    "wbc count": {"unit": "10^3/uL", "low": 4.0, "high": 11.0, "source": "NIH",
                  "aliases": ["white blood cell count", "wbc", "leukocyte count", "leucocyte count",
                              "total leucocyte count", "total leukocyte count", "tlc", "total wbc count",
                              "white blood cells", "total white blood cell count"],
                  "display": "WBC Count"},
    "rbc count": {"unit": "10^6/uL", "low": 4.2, "high": 5.9, "source": "NIH",
                  "aliases": ["red blood cell count", "rbc", "total rbc count", "red blood cells",
                              "erythrocyte count"],
                  "display": "RBC Count"},
    "platelet count": {"unit": "10^3/uL", "low": 150, "high": 450, "source": "Mayo Clinic",
                       "aliases": ["platelets", "plt", "platelet", "thrombocyte count"],
                       "display": "Platelet Count"},
    "mcv": {"unit": "fL", "low": 80, "high": 100, "source": "Mayo Clinic",
            "aliases": ["mean corpuscular volume", "mean cell volume"], "display": "MCV"},
    "mch": {"unit": "pg", "low": 27, "high": 33, "source": "Mayo Clinic",
            "aliases": ["mean corpuscular hemoglobin", "mean corpuscular haemoglobin",
                        "mean cell hemoglobin"], "display": "MCH"},
    "mchc": {"unit": "g/dL", "low": 32, "high": 36, "source": "Mayo Clinic",
             "aliases": ["mean corpuscular hemoglobin concentration",
                         "mean corpuscular haemoglobin concentration",
                         "mean cell hemoglobin concentration"], "display": "MCHC"},
    "rdw": {"unit": "%", "low": 11.5, "high": 14.5, "source": "Mayo Clinic",
            "aliases": ["red cell distribution width", "rdw cv", "rdw sd"], "display": "RDW"},
    "neutrophils": {"unit": "%", "low": 40, "high": 75, "source": "Mayo Clinic",
                    "aliases": ["neutrophil", "neutrophils percent", "polymorphs", "polymorphonuclear"],
                    "display": "Neutrophils"},
    "lymphocytes": {"unit": "%", "low": 20, "high": 40, "source": "Mayo Clinic",
                    "aliases": ["lymphocyte", "lymphocytes percent"], "display": "Lymphocytes"},
    "monocytes": {"unit": "%", "low": 2, "high": 10, "source": "Mayo Clinic",
                  "aliases": ["monocyte"], "display": "Monocytes"},
    "eosinophils": {"unit": "%", "low": 1, "high": 6, "source": "Mayo Clinic",
                    "aliases": ["eosinophil"], "display": "Eosinophils"},
    "basophils": {"unit": "%", "low": 0, "high": 2, "source": "Mayo Clinic",
                  "aliases": ["basophil"], "display": "Basophils"},
    "esr": {"unit": "mm/hr", "low": 0, "high": 20, "source": "Mayo Clinic",
            "aliases": ["erythrocyte sedimentation rate"], "display": "ESR"},

    # ---- Diabetes ----
    "fasting blood glucose": {"unit": "mg/dL", "low": 70, "high": 99, "source": "WHO / ADA",
                              "aliases": ["fbs", "glucose fasting", "blood sugar fasting", "fasting blood sugar",
                                          "fasting plasma glucose", "fpg", "fasting glucose",
                                          "blood glucose fasting", "glucose f", "plasma glucose fasting"],
                              "display": "Fasting Blood Glucose"},
    "postprandial blood glucose": {"unit": "mg/dL", "low": 70, "high": 140, "source": "WHO / ADA",
                                   "aliases": ["ppbs", "post prandial blood sugar", "postprandial glucose",
                                               "blood sugar pp", "glucose pp", "post prandial glucose",
                                               "blood glucose post prandial", "2 hr post prandial glucose"],
                                   "display": "Postprandial Blood Glucose"},
    "hba1c": {"unit": "%", "low": 4.0, "high": 5.6, "source": "ADA / WHO",
              "aliases": ["hbaic", "hbalc", "hba1", "glycated hemoglobin", "glycosylated hemoglobin", "a1c", "hb a1c", "hba1 c",
                          "glycated haemoglobin", "glycosylated haemoglobin", "hemoglobin a1c"],
              "display": "HbA1c"},

    # ---- Lipids ----
    "total cholesterol": {"unit": "mg/dL", "low": 0, "high": 200, "source": "NIH / AHA",
                          "aliases": ["cholesterol total", "cholesterol", "serum cholesterol", "t cholesterol",
                                      "total cholesterol serum"],
                          "display": "Total Cholesterol"},
    "ldl cholesterol": {"unit": "mg/dL", "low": 0, "high": 100, "source": "AHA",
                        "aliases": ["lol cholesterol", "ldl", "ldl c", "ldl cholesterol direct", "cholesterol ldl",
    "low density lipoprotein", "direct ldl", "ldl direct"], "display": "LDL Cholesterol"},
    "hdl cholesterol": {"unit": "mg/dL", "low": 40, "high": 60, "source": "AHA",
                        "aliases": ["hdl", "hdl c", "cholesterol hdl", "high density lipoprotein"],
                        "display": "HDL Cholesterol"},
    "vldl cholesterol": {"unit": "mg/dL", "low": 2, "high": 30, "source": "AHA",
                         "aliases": ["vldl", "vldl c", "cholesterol vldl"], "display": "VLDL Cholesterol"},
    "non hdl cholesterol": {"unit": "mg/dL", "low": 0, "high": 130, "source": "AHA",
                            "aliases": ["non hdl", "non hdl c", "cholesterol non hdl"],
                            "display": "Non-HDL Cholesterol"},
    "triglycerides": {"unit": "mg/dL", "low": 0, "high": 150, "source": "AHA",
                      "aliases": ["tg", "triglyceride", "serum triglycerides", "triglycerides serum"],
                      "display": "Triglycerides"},

    # ---- Thyroid ----
    "tsh": {"unit": "uIU/mL", "low": 0.4, "high": 4.0, "source": "NIH / ATA",
            "aliases": ["thyroid stimulating hormone", "tsh ultrasensitive", "tsh 3rd generation",
                        "ultra sensitive tsh"], "display": "TSH"},
    "t3": {"unit": "ng/dL", "low": 80, "high": 200, "source": "NIH / ATA",
           "aliases": ["total t3", "triiodothyronine", "t3 total", "tri iodothyronine"], "display": "T3"},
    "t4": {"unit": "ug/dL", "low": 5.0, "high": 12.0, "source": "NIH / ATA",
           "aliases": ["total t4", "thyroxine", "t4 total"], "display": "T4"},
    "free t4": {"unit": "ng/dL", "low": 0.8, "high": 1.8, "source": "NIH / ATA",
                "aliases": ["ft4", "free thyroxine", "t4 free"], "display": "Free T4"},

    # ---- Vitamins / minerals ----
    "vitamin d": {"unit": "ng/mL", "low": 30, "high": 100, "source": "NIH ODS",
                  "aliases": ["25 oh vitamin d", "vitamin d3", "25 hydroxyvitamin d", "vit d",
                              "vitamin d 25 hydroxy", "vitamin d total", "25 hydroxy vitamin d",
                              "vitamin d 25 oh", "vit d 25 oh", "25 oh vit d"],
                  "display": "Vitamin D"},
    "vitamin b12": {"unit": "pg/mL", "low": 200, "high": 900, "source": "NIH ODS",
                    "aliases": ["b12", "cobalamin", "vit b12", "cyanocobalamin", "vitamin b 12"],
                    "display": "Vitamin B12"},
    "serum iron": {"unit": "ug/dL", "low": 60, "high": 170, "source": "NIH ODS",
                   "aliases": ["iron", "iron serum"], "display": "Serum Iron"},
    "ferritin": {"unit": "ng/mL", "low": 20, "high": 250, "source": "NIH ODS",
                 "aliases": ["serum ferritin"], "display": "Ferritin"},
    "calcium": {"unit": "mg/dL", "low": 8.6, "high": 10.3, "source": "Mayo Clinic",
                "aliases": ["serum calcium", "calcium total", "total calcium"], "display": "Calcium"},
    "phosphorus": {"unit": "mg/dL", "low": 2.5, "high": 4.5, "source": "Mayo Clinic",
                   "aliases": ["phosphate", "inorganic phosphorus", "serum phosphorus", "phosphorous"],
                   "display": "Phosphorus"},
    "magnesium": {"unit": "mg/dL", "low": 1.7, "high": 2.2, "source": "Mayo Clinic",
                  "aliases": ["serum magnesium", "mg"], "display": "Magnesium"},

    # ---- Kidney ----
    "serum creatinine": {"unit": "mg/dL", "low": 0.6, "high": 1.3, "source": "NIH / NKF",
                         "aliases": ["creatinine", "creatinine serum", "s creatinine", "creat"],
                         "display": "Serum Creatinine"},
    "urea": {"unit": "mg/dL", "low": 15, "high": 45, "source": "Mayo Clinic",
             "aliases": ["blood urea", "serum urea", "urea serum"], "display": "Urea"},
    "blood urea nitrogen": {"unit": "mg/dL", "low": 7, "high": 20, "source": "Mayo Clinic",
                            "aliases": ["bun", "urea nitrogen", "blood urea nitrogen bun"],
                            "display": "Blood Urea Nitrogen"},
    "uric acid": {"unit": "mg/dL", "low": 3.5, "high": 7.2, "source": "Mayo Clinic",
                  "aliases": ["serum uric acid", "uric acid serum"], "display": "Uric Acid"},

    # ---- Liver ----
    "sgpt": {"unit": "U/L", "low": 7, "high": 56, "source": "Mayo Clinic",
             "aliases": ["alt", "alanine aminotransferase", "sgpt alt", "alt sgpt", "alanine transaminase"],
             "display": "SGPT (ALT)"},
    "sgot": {"unit": "U/L", "low": 8, "high": 45, "source": "Mayo Clinic",
             "aliases": ["ast", "aspartate aminotransferase", "sgot ast", "ast sgot",
                         "aspartate transaminase"], "display": "SGOT (AST)"},
    "alkaline phosphatase": {"unit": "U/L", "low": 44, "high": 147, "source": "Mayo Clinic",
                             "aliases": ["alp", "alk phos", "alkaline phosphatase alp"],
                             "display": "Alkaline Phosphatase"},
    "total bilirubin": {"unit": "mg/dL", "low": 0.1, "high": 1.2, "source": "Mayo Clinic",
                        "aliases": ["bilirubin total", "bilirubin", "serum bilirubin total",
                                    "t bilirubin"], "display": "Total Bilirubin"},
    "direct bilirubin": {"unit": "mg/dL", "low": 0.0, "high": 0.3, "source": "Mayo Clinic",
                         "aliases": ["bilirubin direct", "conjugated bilirubin", "d bilirubin"],
                         "display": "Direct Bilirubin"},
    "albumin": {"unit": "g/dL", "low": 3.5, "high": 5.0, "source": "Mayo Clinic",
                "aliases": ["serum albumin"], "display": "Albumin"},
    "total protein": {"unit": "g/dL", "low": 6.0, "high": 8.3, "source": "Mayo Clinic",
                      "aliases": ["protein total", "serum protein", "serum total protein"],
                      "display": "Total Protein"},

    # ---- Electrolytes ----
    "sodium": {"unit": "mEq/L", "low": 135, "high": 145, "source": "Mayo Clinic",
               "aliases": ["na", "serum sodium", "sodium na"], "display": "Sodium"},
    "potassium": {"unit": "mEq/L", "low": 3.5, "high": 5.1, "source": "Mayo Clinic",
                  "aliases": ["k", "serum potassium", "potassium k"], "display": "Potassium"},
    "chloride": {"unit": "mEq/L", "low": 98, "high": 107, "source": "Mayo Clinic",
                 "aliases": ["cl", "serum chloride", "chloride cl"], "display": "Chloride"},
}

# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------
def _clean(s: str) -> str:
    s = s.lower().replace("&", " and ").replace("\u00b5", "u").replace("\u03bc", "u")
    s = re.sub(r"\b(?:[a-z]\.){2,}[a-z]?", lambda m: m.group(0).replace(".", ""), s)  # S.G.O.T. -> sgot
    s = re.sub(r"[^a-z0-9%+\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# flat alias -> canonical name lookup, built once at import time
_ALIAS_INDEX: Dict[str, str] = {}
for _canonical, _info in REFERENCE_RANGES.items():
    _ALIAS_INDEX[_clean(_canonical)] = _canonical
    for _alias in _info.get("aliases", []):
        _ALIAS_INDEX[_clean(_alias)] = _canonical
    if _info.get("display"):
        _ALIAS_INDEX[_clean(_info["display"])] = _canonical

_QUALIFIERS = {"serum", "plasma", "blood", "level", "levels", "test", "estimation", "the", "sr", "s"}

# analytical-method / technology words that some labs print in an extra column
# right after the test name ("TOTAL CHOLESTEROL   CHOD-POD   212 mg/dL ...")
_METHOD_PHRASES = sorted([
    "flow cytometry", "electrical impedance", "impedance", "photometry", "spectrophotometry",
    "photometric", "cyanmethemoglobin", "chod pod", "cod pod", "gpo pod", "god pod", "calculated",
    "calculation", "computed", "direct", "enzymatic", "colorimetric", "hplc", "clia", "cmia", "eclia",
    "elisa", "jaffe", "jaffe kinetic", "kinetic", "hexokinase", "ise", "turbidimetry", "nephelometry",
    "immunoturbidimetry", "ifcc", "arsenazo", "bcg", "biuret", "diazo", "urease", "chemiluminescence",
    "automated", "microscopy", "microscopic", "vanadate", "uv", "pod", "ecl", "immunoassay",
], key=len, reverse=True)


def _strip_methods(c: str) -> str:
    changed = True
    while changed:
        changed = False
        for ph in _METHOD_PHRASES:
            if c.endswith(" " + ph):
                c = c[: -len(ph) - 1]
                changed = True
                break
    return c
_TOKENISED = [(a.split(), c) for a, c in _ALIAS_INDEX.items()]


def _fuzzy_lookup(cleaned: str) -> Optional[str]:
    """OCR-typo tolerant match. Every token must match exactly, except long
    tokens (>=6 chars) which may differ slightly ('hemoglobln'). Short tokens
    (ldl / hdl / t3 / t4 ...) must match EXACTLY so LDL can never be read as HDL."""
    toks = cleaned.split()
    best, best_score = None, 0.0
    for atoks, canonical in _TOKENISED:
        if len(atoks) != len(toks):
            continue
        score = 0.0
        ok = True
        for t, a in zip(toks, atoks):
            if t == a:
                score += 1.0
            elif len(t) >= 6 and len(a) >= 6:
                r = difflib.SequenceMatcher(None, t, a).ratio()
                if r < 0.85:
                    ok = False
                    break
                score += r
            else:
                ok = False
                break
        if ok and score > best_score:
            best, best_score = canonical, score
    return best


def normalize_parameter_name(raw_name: str) -> Optional[str]:
    """Match a raw (possibly OCR'd) parameter name to a canonical name.
    Returns None when the name is not a known parameter -- it deliberately
    never guesses with substring matching (that used to turn 'Vitamin B' into
    Vitamin B12 and 'Mean Corpuscular Hemoglobin' into Hemoglobin)."""
    if not raw_name:
        return None
    raw = raw_name.strip()
    variants = [raw]
    m = re.match(r"^(.*?)\((.*?)\)\s*(.*)$", raw)
    if m:
        variants += [(m.group(1) + " " + m.group(3)).strip(), m.group(2)]
    cleaned = [c for c in (_clean(v) for v in variants) if c]

    for c in cleaned:
        if c in _ALIAS_INDEX:
            return _ALIAS_INDEX[c]
    for c in cleaned:
        c1 = _strip_methods(c)
        for cand in (c1, " ".join(t for t in c1.split() if t not in _QUALIFIERS)):
            if cand and cand in _ALIAS_INDEX:
                return _ALIAS_INDEX[cand]
    for c in cleaned:
        hit = _fuzzy_lookup(_strip_methods(c))
        if hit:
            return hit
    return None


def is_exact_alias(raw_name: str) -> bool:
    """True if the whole string (no parenthesis tricks, no fuzzy) is a known alias."""
    return _clean(raw_name) in _ALIAS_INDEX


def display_name(canonical: str) -> str:
    info = REFERENCE_RANGES.get(canonical)
    return (info or {}).get("display") or canonical.title()


def get_reference(canonical_name: str) -> Optional[Dict]:
    return REFERENCE_RANGES.get(canonical_name)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def classify_with_range(value: Optional[float], low: Optional[float], high: Optional[float]) -> str:
    """normal | low | high | critical_low | critical_high | unknown, against an
    explicit (low, high) band. Either bound may be None (e.g. '<200')."""
    if value is None or (low is None and high is None):
        return "unknown"
    if low is not None and high is not None and high > low:
        span = high - low
    else:
        span = abs(high if high is not None else low) or 1.0
    if low is not None and value < low:
        return "critical_low" if value < low - 0.5 * span else "low"
    if high is not None and value > high:
        return "critical_high" if value > high + 0.5 * span else "high"
    return "normal"


def classify_value(canonical_name: str, value: float) -> str:
    """Fallback: classify against the built-in table."""
    ref = get_reference(canonical_name)
    if not ref or value is None:
        return "unknown"
    return classify_with_range(value, ref["low"], ref["high"])


# ---------------------------------------------------------------------------
# Unit handling (Indian labs print WBC as 6500 cells/cumm, platelets as
# '2.5 lakhs/cumm', glucose in mmol/L in some countries ...)
# ---------------------------------------------------------------------------
def normalize_unit(u: Optional[str]) -> str:
    if not u:
        return ""
    s = u.strip().lower().replace("\u00b5", "u").replace("\u03bc", "u")
    s = s.replace("\u00b3", "^3").replace("\u2076", "^6").replace("*", "^").replace(" ", "")
    s = re.sub(r"^x(?=10)", "", s)
    s = re.sub(r"^10(?:\^|\*)?4?([36])/", r"10^\1/", s)   # OCR: 10^3/uL read as 1043/uL or 103/uL
    s = re.sub(r"/d[t1i|]$", "/dl", s)                       # OCR: mg/dt, mg/d1
    s = re.sub(r"/m[1i|]$", "/ml", s)                        # OCR: ng/m1
    s = re.sub(r"(?:mm\^?3|cmm)$", "cumm", s)
    s = s.replace("thou/", "10^3/").replace("thousand/", "10^3/").replace("k/", "10^3/")
    s = s.replace("million/", "10^6/").replace("mill/", "10^6/").replace("mil/", "10^6/")
    s = s.replace("lakhs", "lakh")
    s = s.replace("gms/dl", "g/dl").replace("gm/dl", "g/dl").replace("gm%", "g/dl").replace("g%", "g/dl")
    s = s.replace("mgs/dl", "mg/dl").replace("mcg/dl", "ug/dl")
    s = s.replace("iu/l", "u/l").replace("miu/l", "uiu/ml").replace("mu/l", "uiu/ml")
    s = s.replace("10^9/l", "10^3/ul").replace("10^12/l", "10^6/ul")
    s = s.replace("10^3/cumm", "10^3/ul").replace("10^6/cumm", "10^6/ul")
    s = {"ug/l": "ng/ml", "ng/l": "pg/ml", "cells/cumm": "/cumm", "cells/ul": "/cumm",
         "/ul": "/cumm", "lakh/cumm": "lakh/cumm", "lakh/ul": "lakh/cumm",
         "mm/1sthour": "mm/hr", "mm/h": "mm/hr", "mmol/l": "mmol/l"}.get(s, s)
    return s


def _lin(f: float) -> Callable[[float], float]:
    return lambda v: v * f


_IDENT = lambda v: v  # noqa: E731

# (canonical, normalised source unit) -> function converting to the table unit
_CONVERSIONS: Dict[Tuple[str, str], Callable[[float], float]] = {
    ("wbc count", "/cumm"): _lin(1 / 1000),
    ("platelet count", "/cumm"): _lin(1 / 1000),
    ("platelet count", "lakh/cumm"): _lin(100),
    ("rbc count", "/cumm"): _lin(1 / 1_000_000),
    ("fasting blood glucose", "mmol/l"): _lin(18.016),
    ("postprandial blood glucose", "mmol/l"): _lin(18.016),
    ("hba1c", "mmol/mol"): lambda v: v / 10.929 + 2.15,
    ("total cholesterol", "mmol/l"): _lin(38.67),
    ("ldl cholesterol", "mmol/l"): _lin(38.67),
    ("hdl cholesterol", "mmol/l"): _lin(38.67),
    ("vldl cholesterol", "mmol/l"): _lin(38.67),
    ("non hdl cholesterol", "mmol/l"): _lin(38.67),
    ("triglycerides", "mmol/l"): _lin(88.57),
    ("serum creatinine", "umol/l"): _lin(1 / 88.4),
    ("hemoglobin", "g/l"): _lin(0.1),
    ("mchc", "g/l"): _lin(0.1),
    ("hematocrit", "l/l"): _lin(100),
    ("calcium", "mmol/l"): _lin(4.008),
    ("vitamin b12", "pmol/l"): _lin(1.355),
    ("vitamin d", "nmol/l"): _lin(0.4006),
    ("urea", "mmol/l"): _lin(6.006),
    ("blood urea nitrogen", "mmol/l"): _lin(2.801),
    ("uric acid", "umol/l"): _lin(1 / 59.48),
    ("total bilirubin", "umol/l"): _lin(1 / 17.1),
    ("direct bilirubin", "umol/l"): _lin(1 / 17.1),
    ("albumin", "g/l"): _lin(0.1),
    ("total protein", "g/l"): _lin(0.1),
    ("t4", "nmol/l"): _lin(0.0777),
    ("free t4", "pmol/l"): _lin(0.0777),
    ("serum iron", "umol/l"): _lin(5.585),
    ("magnesium", "mmol/l"): _lin(2.43),
    ("phosphorus", "mmol/l"): _lin(3.097),
}

# units that mean the same thing as the table unit for a given table unit
_EQUIVALENT = {
    "meq/l": {"mmol/l"},
    "ug/dl": {"mcg/dl"},
}


def convert_to_standard(canonical: str, unit: Optional[str]) -> Tuple[Callable[[float], float], str, str]:
    """Returns (convert_fn, standard_unit, state).
    state: 'same' | 'converted' | 'no_unit' | 'unknown_unit'."""
    ref = REFERENCE_RANGES.get(canonical)
    if not ref:
        return _IDENT, unit or "", "unknown_unit"
    std_unit = ref["unit"]
    std_norm = normalize_unit(std_unit)
    u = normalize_unit(unit)
    if not u:
        return _IDENT, std_unit, "no_unit"
    if u == std_norm or u in _EQUIVALENT.get(std_norm, set()) or (std_norm == "meq/l" and u == "mmol/l"):
        return _IDENT, std_unit, "same"
    fn = _CONVERSIONS.get((canonical, u))
    if fn:
        return fn, std_unit, "converted"
    return _IDENT, unit or "", "unknown_unit"
