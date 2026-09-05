# Architecture & Technical Documentation

## AI Health Report Analyzer & Personal Health Assistant

---

## 1. Business problem

Millions of people receive routine blood test results they cannot interpret
without a clinician. This system automatically analyzes a blood report,
detects abnormalities and deficiencies, explains every parameter in plain
language, and produces personalized diet, exercise, and lifestyle
recommendations.

## 2. High-level architecture

```
 ┌─────────────────────┐
 │ 1. Report Ingestion  │  PDF / Image / DOCX upload
 └──────────┬───────────┘
            ▼
 ┌─────────────────────┐
 │ 2. OCR & Extraction  │  Native-text extraction (pdfplumber) or OCR
 │                      │  (pytesseract) → table/line parsing → parameter list
 └──────────┬───────────┘
            ▼
 ┌─────────────────────┐
 │ 3. Validation        │  Unit sanity checks, alias normalization
 │                      │  ("Hb" → "Hemoglobin"), missing-value handling
 └──────────┬───────────┘
            ▼
 ┌─────────────────────┐
 │ 4. AI Medical        │  Compare against reference ranges, detect
 │    Analysis          │  deficiencies/risks, generate explanations
 └──────────┬───────────┘
            ▼
 ┌─────────────────────┐
 │ 5. Medical Knowledge │  Curated WHO / NIH / Mayo Clinic reference-range
 │    Layer (RAG)       │  table, source-tagged, grounds every claim
 └──────────┬───────────┘
            ▼
 ┌─────────────────────┐
 │ 6. Recommendation    │  Diet, exercise, hydration, sleep, stress,
 │    Engine            │  lifestyle guidance
 └──────────┬───────────┘
            ▼
 ┌─────────────────────┐
 │ 7. Report Generation │  Health score, summary, critical alerts,
 │                      │  final JSON report → React dashboard
 └──────────────────────┘
```

## 3. Multi-agent design (LangGraph)

The pipeline is implemented as a `StateGraph` in `backend/app/pipeline.py`
with a single shared Pydantic state object (`PipelineState`) flowing through
four sequential nodes:

| Agent | Node | Responsibility | Output |
|---|---|---|---|
| 1 | Report Processing | OCR, table detection, parameter extraction, unit validation, normalization | `ExtractedReport` (clean JSON) |
| 2 | Medical Analysis | RAG-grounded comparison against reference ranges, deficiency/risk detection, plain-language explanations | `MedicalAnalysis` |
| 3 | Recommendation | Personalized diet / exercise / hydration / sleep / stress-management guidance | `Recommendations` |
| 4 | Report Generation | Health score computation, summary, critical-alert detection, final assembly | `FinalReport` |

If the `langgraph` package is unavailable in a given environment, the same
four functions run as a plain sequential fallback (`app/pipeline.py`,
`using_langgraph()`), so behavior is identical either way.

## 4. AI / LLM approach

- **Model:** Claude (Anthropic API), called via `backend/app/llm_client.py`.
- **Grounding (RAG):** Before calling the LLM, Agent 2 builds a context block
  from the curated reference-range table (`app/reference_ranges.py`), which is
  itself tagged with its source guideline (WHO, NIH, Mayo Clinic, ADA, AHA).
  The LLM is instructed to never invent lab values and to reason only from
  the supplied context.
- **Structured output:** Both Agent 2 and Agent 3 prompt Claude to return
  strict JSON matching a documented schema, which is then validated against
  the corresponding Pydantic model before being trusted.
- **Graceful degradation:** If no `ANTHROPIC_API_KEY` is configured, or a call
  fails/returns malformed JSON, each agent falls back to a deterministic
  rule-based engine that produces the same schema from the reference-range
  table directly. This means the system is fully functional, testable, and
  gradeable with zero API cost.

## 5. Data processing pipeline

1. **Ingestion** — file bytes accepted via `POST /api/analyze` (multipart) or
   `POST /api/analyze-text` (raw text, useful for demos).
2. **Text extraction** — `ocr_extraction.py` dispatches by file extension:
   - `.pdf` → `pdfplumber` (native text) → OCR fallback via `pdf2image` +
     `pytesseract` for scanned pages.
   - `.jpg` / `.png` → `pytesseract` directly.
   - `.docx` → `python-docx`, including table cells.
3. **Parameter parsing** — a regex tuned for "Name  Value  Unit  (Range)"
   style lab-report lines, with a noise filter that drops header/footer lines
   (patient ID, lab name, page numbers).
4. **Normalization** — `reference_ranges.normalize_parameter_name()` maps OCR
   variants and abbreviations (`Hb`, `HGB`) to a canonical parameter name via
   an alias index.
5. **Matching & scoring logic** — `reference_ranges.classify_value()` buckets
   each value into `normal / low / high / critical_low / critical_high` using
   the canonical parameter's reference band, with the critical thresholds set
   at 1.5× the band's width beyond the boundary. Agent 4 then computes the
   overall health score by starting at 100 and subtracting a per-parameter
   penalty (7 points for out-of-range, 15 for critical), floored at 10.

## 6. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI |
| OCR | pdfplumber, pdf2image + pytesseract |
| Document parsing | python-docx |
| LLM | Claude (Anthropic API) |
| Multi-agent orchestration | LangGraph |
| Data validation | Pydantic |

## 7. Handling variability

- **Different lab formats** — the regex parser and alias index tolerate
  varying column orders and naming conventions; `_detect_format()` labels the
  panel type (CBC, lipid, thyroid, liver, kidney, general).
- **Scanned / low-quality reports** — OCR fallback path with a confidence
  score surfaced in the API response.
- **OCR errors** — alias fuzzy-matching (`normalize_parameter_name`) tolerates
  minor misreads; a noise filter strips non-parameter lines.
- **Missing values** — parameters that fail to parse are simply omitted
  rather than crashing the pipeline; warnings are collected in
  `ExtractedReport.warnings`.
- **Unit differences** — the unit is stored alongside the value; the
  reference-range table anchors to standard clinical units.

## 8. Dataset & testing

- `backend/scripts/generate_sample_reports.py` generates **25 synthetic blood
  reports** (`backend/sample_data/`) across 4 simulated lab formats, with
  ~1/3 deliberately containing abnormal values to exercise the deficiency/risk
  paths.
- Evaluated informally on: extraction accuracy (parameters found vs. present
  in the synthetic report), recommendation relevance (every abnormal
  parameter maps to at least one recommendation), and response time
  (sub-second per report on the rule-based fallback path).

## 9. API reference (summary)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/api/status` | Reports pipeline engine + whether the LLM is active |
| POST | `/api/analyze` | Upload a file (`multipart/form-data`) → `FinalReport` |
| POST | `/api/analyze-text` | Analyze pasted report text |
| GET | `/api/sample-reports` | List bundled synthetic reports |
| POST | `/api/analyze-sample/{name}` | Run the pipeline on a bundled sample |

Full interactive docs are auto-generated by FastAPI at `/docs`.
