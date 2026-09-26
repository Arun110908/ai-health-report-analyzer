# Code guide

This guide is for explaining the project in a viva or review. It describes
where each part of the code runs and why it exists. The application is an
academic health-information tool, not a diagnostic system.

## Request flow

```text
React dashboard → FastAPI route → document text extraction → Agent 1 parser
→ Agent 2 medical analysis + optional ML estimate → Agent 3 recommendations
→ Agent 4 final JSON → dashboard cards
```

## Backend files

| File | What it does |
| --- | --- |
| `app/main.py` | Creates FastAPI, accepts uploads, chooses a reader by suffix, creates `PipelineState`, and returns `FinalReport` JSON. `POST /api/analyze-batch` accepts up to 10 files in one request and analyzes each independently (one file's failure never blocks the others). `GET /health` is a simple liveness check. |
| `app/models.py` | Defines the Pydantic input, intermediate, and response shapes. This prevents agents and API routes from passing unstructured dictionaries. |
| `app/pipeline.py` | Wires the four functions as a LangGraph sequence. If LangGraph is unavailable, it runs exactly the same functions sequentially. |
| `app/ocr_extraction.py` | Reads native PDFs, scanned PDFs/images, DOCX files, and report text. It also turns text rows into parameter/value/unit/range records. |
| `app/reference_ranges.py` | Holds the offline reference data, aliases, OCR typo-safe name matching, unit conversion, and normal/low/high classification helpers. Printed report ranges take priority. |
| `app/llm_client.py` | Calls Claude only when `ANTHROPIC_API_KEY` exists. Otherwise it returns control to the safe rule-based paths. |
| `app/ml_risk.py` | Optional GlucoSight-style LightGBM + KNN soft-voting module and SHAP explanation adapter. It refuses missing inputs and does not save inputs. |
| `app/agents/agent1_report_processing.py` | Normalises extracted rows, applies conversions, removes duplicates, uses printed reference ranges first, and adds OCR warnings. |
| `app/agents/agent2_medical_analysis.py` | Builds simple explanations, possible deficiencies, and risks from the structured report. It also requests the optional ML demo output. |
| `app/agents/agent3_recommendation.py` | Produces safe lifestyle recommendations from abnormal parameters; Claude output is optional. |
| `app/agents/agent4_report_generation.py` | Calculates the display health score, highlights critical values, and assembles the final response. |

### September 2026 review: real-report bug fixes

A real de-identified Sterling Accuris pathology PDF was used to test the
parser end to end (not just synthetic data). It exposed and fixed:
- A bold H/L flag glued directly onto a value with no space (`H10570`)
  silently broke extraction for that row entirely.
- A name and its value split across two lines (`Vitamin B12` / `L < 148 ...`)
  were never joined, dropping the parameter.
- Method words not in the known list ("Microscopic", "Derived") blocked
  alias matching, so rows like Neutrophils/Lymphocytes fell back to an
  "unknown parameter" path and were silently dropped when their line had an
  ambiguous multi-band reference range.
- An explanatory sentence in the report body ("Microalbuminuria is defined
  as...") was briefly misread as a parameter/value pair.
- A multi-word unit split across a space ("micro g/dL") only kept the first
  word; "Up to 5.0" style range phrasing was briefly captured as a fake unit.

All are fixed and covered by `backend/tests_real_reports/` (see
`tests_real_reports/README.md` for exactly how that fixture was verified —
it is a hand-checked regression snapshot, not an independent benchmark).
Extraction on that real report is 60/60 parameters, 100% status-correct,
after the fixes (was silently dropping ~4 real values before).

### DOCX conversion: where it really happens

`main.py` calls `_extract_bytes()` for every upload. When a filename ends in
`.docx`, it calls `ocr_extraction.extract_text_from_docx()`. That function uses
`python-docx` to collect document paragraphs **and every table row**, joins them
into plain text, and returns the text to Agent 1. It does not convert a DOCX to
a separate `.txt` file on disk; it converts it in memory because the parser only
needs text and no patient report should be stored unnecessarily.

### OCR improvements

The OCR path corrects EXIF rotation, uses grayscale/autocontrast, enlarges small
phone photos, boosts contrast, lightly sharpens characters, and tells Tesseract
to preserve spacing in table-like text. Native PDF text is preferred only when
it is sufficiently readable. The parser also handles H/L markers attached to a
number such as `H10570` and markers separated from the result such as `B12 L <
148`.

## ML demo files

| File | What it does |
| --- | --- |
| `scripts/generate_demo_risk_data.py` | Creates transparent, clearly marked synthetic data for a classroom demo. |
| `scripts/train_risk_model.py` | Standardises the eight GlucoSight features, tunes LightGBM, trains KNN, averages their probabilities, measures hold-out metrics, and saves one local artifact. |
| `app/ml_risk.py` | Loads that artifact only after all eight inputs are present. It reports model agreement and the five largest SHAP contributions. |

The required ML inputs are age, BMI, systolic BP, fasting glucose, fasting
insulin, total cholesterol, HbA1c, and post-meal glucose. Age/BMI/BP/insulin are
optional fields in the UI; the lab report supplies the other values when present.
The app returns `insufficient_data` instead of inventing medical values.

## Frontend files

| File/folder | What it does |
| --- | --- |
| `src/App.jsx` | Owns dashboard state, calls the API, and selects upload or report view. |
| `src/api.js` | Contains all browser-to-FastAPI requests. |
| `src/components/UploadPanel.jsx` | Handles file selection, drag/drop, bundled sample selection, and optional ML-context fields. |
| `src/components/VitalsDial.jsx` | Animated overall-score gauge. |
| `src/components/ParameterTable.jsx` | Colour-coded parameter trace list, range bars, and status labels. |
| `src/components/MLRiskPanel.jsx` | Shows the optional ensemble score or explains exactly what is missing. |
| `src/components/AlertBanner.jsx` | Renders urgent report warnings. |
| `src/components/InsightsPanel.jsx` | Renders deficiency and health-risk cards. |
| `src/components/RecommendationsPanel.jsx` | Renders diet, activity, and lifestyle guidance. |
| `src/components/ExplanationsPanel.jsx` | Renders simple explanations for each parameter. |
| `src/icons.jsx` and `src/index.css` | Self-contained SVG icons and the responsive AXD vitals-monitor design. |

## Verification commands

```bash
cd backend
python scripts/evaluate.py                          # 25 synthetic reports
python scripts/evaluate.py --dir tests_realistic     # 5 hand-written realistic formats
python scripts/evaluate.py --dir tests_real_reports  # the real Sterling Accuris PDF
python scripts/evaluate_ocr.py --quality poor        # blurry-photo OCR, rendered+degraded
pytest ../tests/test_api.py -q                       # if you added an API test file

# train the risk-model artifact locally (Docker does this automatically at build time)
python scripts/generate_demo_risk_data.py --rows 600
python scripts/train_risk_model.py --input data/demo_metabolic_risk.csv

# exercise the new multi-file endpoint
curl -X POST http://localhost:8000/api/analyze-batch \
  -F "files=@report1.pdf" -F "files=@report2.docx"
```

The bundled extraction test data are synthetic/hand-written. For a real accuracy
claim, use de-identified reports with independently labelled ground truth.
