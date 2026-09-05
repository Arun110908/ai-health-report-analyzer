"""
Medical Knowledge Layer (offline component of the RAG system).

This module ships a curated, source-cited reference-range table compiled
from publicly available WHO / NIH / Mayo Clinic guideline summaries.
It acts as:
  1. The grounding/context passed into the LLM prompts (retrieval step),
  2. A deterministic fallback so the app still works with zero LLM cost /
     no internet access (used by the rule-based fallback engine).

Each entry: (unit, low, high, source)
Ranges are for general adult reference and are intentionally
conservative -- always show a "consult your doctor" disclaimer.
"""

from typing import Dict, Tuple, Optional

# name (normalized, lowercase) -> (unit, low, high, source)
REFERENCE_RANGES: Dict[str, Dict] = {
    "hemoglobin": {"unit": "g/dL", "low": 13.0, "high": 17.0, "source": "WHO / Mayo Clinic",
                   "aliases": ["hb", "hgb"]},
    "hematocrit": {"unit": "%", "low": 38.8, "high": 50.0, "source": "Mayo Clinic",
                   "aliases": ["hct", "pcv"]},
    "wbc count": {"unit": "10^3/uL", "low": 4.0, "high": 11.0, "source": "NIH",
                  "aliases": ["white blood cell count", "wbc", "leukocyte count"]},
    "rbc count": {"unit": "10^6/uL", "low": 4.2, "high": 5.9, "source": "NIH",
                  "aliases": ["red blood cell count", "rbc"]},
    "platelet count": {"unit": "10^3/uL", "low": 150, "high": 450, "source": "Mayo Clinic",
                        "aliases": ["platelets", "plt"]},
    "fasting blood glucose": {"unit": "mg/dL", "low": 70, "high": 99, "source": "WHO / ADA",
                               "aliases": ["fbs", "glucose fasting", "blood sugar fasting"]},
    "hba1c": {"unit": "%", "low": 4.0, "high": 5.6, "source": "ADA / WHO",
              "aliases": ["glycated hemoglobin", "a1c"]},
    "total cholesterol": {"unit": "mg/dL", "low": 0, "high": 200, "source": "NIH / AHA",
                           "aliases": ["cholesterol total", "cholesterol"]},
    "ldl cholesterol": {"unit": "mg/dL", "low": 0, "high": 100, "source": "AHA",
                         "aliases": ["ldl"]},
    "hdl cholesterol": {"unit": "mg/dL", "low": 40, "high": 60, "source": "AHA",
                         "aliases": ["hdl"]},
    "triglycerides": {"unit": "mg/dL", "low": 0, "high": 150, "source": "AHA",
                       "aliases": ["tg"]},
    "tsh": {"unit": "uIU/mL", "low": 0.4, "high": 4.0, "source": "NIH / ATA",
            "aliases": ["thyroid stimulating hormone"]},
    "vitamin d": {"unit": "ng/mL", "low": 30, "high": 100, "source": "NIH ODS",
                  "aliases": ["25-oh vitamin d", "vitamin d3", "25-hydroxyvitamin d"]},
    "vitamin b12": {"unit": "pg/mL", "low": 200, "high": 900, "source": "NIH ODS",
                    "aliases": ["b12", "cobalamin"]},
    "serum creatinine": {"unit": "mg/dL", "low": 0.6, "high": 1.3, "source": "NIH / NKF",
                          "aliases": ["creatinine"]},
    "urea": {"unit": "mg/dL", "low": 7, "high": 20, "source": "Mayo Clinic",
             "aliases": ["blood urea nitrogen", "bun"]},
    "sgpt": {"unit": "U/L", "low": 7, "high": 56, "source": "Mayo Clinic",
             "aliases": ["alt", "alanine aminotransferase"]},
    "sgot": {"unit": "U/L", "low": 8, "high": 45, "source": "Mayo Clinic",
             "aliases": ["ast", "aspartate aminotransferase"]},
    "serum iron": {"unit": "ug/dL", "low": 60, "high": 170, "source": "NIH ODS",
                   "aliases": ["iron"]},
    "ferritin": {"unit": "ng/mL", "low": 20, "high": 250, "source": "NIH ODS",
                 "aliases": []},
    "calcium": {"unit": "mg/dL", "low": 8.6, "high": 10.3, "source": "Mayo Clinic",
                "aliases": ["serum calcium"]},
    "sodium": {"unit": "mEq/L", "low": 135, "high": 145, "source": "Mayo Clinic",
               "aliases": ["na"]},
    "potassium": {"unit": "mEq/L", "low": 3.5, "high": 5.1, "source": "Mayo Clinic",
                  "aliases": ["k"]},
}

# flat alias -> canonical name lookup, built once at import time
_ALIAS_INDEX: Dict[str, str] = {}
for canonical, info in REFERENCE_RANGES.items():
    _ALIAS_INDEX[canonical] = canonical
    for alias in info.get("aliases", []):
        _ALIAS_INDEX[alias.lower()] = canonical


def normalize_parameter_name(raw_name: str) -> Optional[str]:
    """Match a raw OCR'd parameter name (e.g. 'Hb', 'HB.') to a canonical name."""
    cleaned = raw_name.strip().lower().strip(".:")
    if cleaned in _ALIAS_INDEX:
        return _ALIAS_INDEX[cleaned]
    # loose contains-match fallback for messy OCR text
    for alias, canonical in _ALIAS_INDEX.items():
        if alias and (alias in cleaned or cleaned in alias):
            return canonical
    return None


def get_reference(canonical_name: str) -> Optional[Dict]:
    return REFERENCE_RANGES.get(canonical_name)


def classify_value(canonical_name: str, value: float) -> str:
    """Return normal | low | high | critical_low | critical_high | unknown."""
    ref = get_reference(canonical_name)
    if not ref or value is None:
        return "unknown"
    low, high = ref["low"], ref["high"]
    span = max(high - low, 1e-6)
    if value < low - 0.5 * span:
        return "critical_low"
    if value < low:
        return "low"
    if value > high + 0.5 * span:
        return "critical_high"
    if value > high:
        return "high"
    return "normal"
