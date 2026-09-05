# Vitals — AI Health Report Analyzer & Personal Health Assistant

An AI system that turns a raw blood report (PDF, scanned image, or DOCX) into a
plain-language health summary: extracted parameters, deficiencies, risks, an
overall health score, and personalized diet / exercise / lifestyle
recommendations — powered by a 4-agent LangGraph pipeline.

> Internship project — Blismos. Built by Arun M.

---

## 1. Architecture at a glance

```
Upload (PDF / Image / DOCX)
        │
        ▼
┌───────────────────────┐
│ Agent 1                │  OCR, table detection, parameter extraction,
│ Report Processing      │  unit validation, normalization
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Agent 2                │  RAG over WHO / NIH / Mayo Clinic reference
│ Medical Analysis       │  ranges → deficiencies, risks, explanations
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Agent 3                │  Personalized diet, exercise, hydration,
│ Recommendation         │  sleep, stress-management guidance
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Agent 4                │  Health score, summary, critical alerts,
│ Report Generation      │  final downloadable report
└───────────┬───────────┘
            ▼
      React dashboard (Vitals)
```

The four agents are wired together with **LangGraph** (`backend/app/pipeline.py`).
Agents 2 and 3 call the **Claude API** when `ANTHROPIC_API_KEY` is set, and
transparently fall back to a deterministic, rule-based engine otherwise — so
the whole system runs end-to-end even with zero API cost, which is what makes
it gradeable/demoable offline.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full breakdown of
technologies, the data pipeline, and the matching/scoring logic.

## 2. Project structure

```
ai-health-report-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app & routes
│   │   ├── pipeline.py             LangGraph wiring
│   │   ├── models.py               Pydantic schemas
│   │   ├── ocr_extraction.py       PDF/Image/DOCX → text
│   │   ├── reference_ranges.py     Offline medical knowledge base (RAG)
│   │   ├── llm_client.py           Claude API wrapper + fallback switch
│   │   └── agents/
│   │       ├── agent1_report_processing.py
│   │       ├── agent2_medical_analysis.py
│   │       ├── agent3_recommendation.py
│   │       └── agent4_report_generation.py
│   ├── scripts/generate_sample_reports.py
│   ├── sample_data/                25 synthetic test reports
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/             UploadPanel, HealthScoreHero, ParameterTable, …
│   └── package.json
├── docs/ARCHITECTURE.md
├── sample_io/                      5 sample inputs + real outputs
└── README.md
```

## 3. Run it locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional — enables real Claude-generated explanations/recommendations.
# Without this the app still fully works via the rule-based engine.
export ANTHROPIC_API_KEY=sk-ant-...

uvicorn app.main:app --reload --port 8000
```

Backend docs: http://localhost:8000/docs

> OCR for scanned PDFs/images additionally needs the **Tesseract** binary
> installed on your OS (`sudo apt install tesseract-poppler-utils poppler-utils`
> on Ubuntu, `brew install tesseract poppler` on macOS). Native-text PDFs and
> DOCX work without it.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the dev server proxies `/api` to `localhost:8000`.

### Quick smoke test (no file needed)

```bash
curl -X POST http://localhost:8000/api/analyze-sample/sample_report_01.txt
```

## 4. Deliverables checklist

| Deliverable | Location |
|---|---|
| Architecture diagram + explanation | `docs/ARCHITECTURE.md` |
| Project documentation | `docs/ARCHITECTURE.md`, this README |
| Source code (complete, structured) | `backend/`, `frontend/` |
| GitHub repository link | see §5 below |
| Sample input & output (≥5) | `sample_io/` |
| Execution instructions | §3 above |
| Dataset for testing (≥20 reports) | `backend/sample_data/` (25 reports) |

## 5. Push this project to GitHub from VS Code

1. Open the project folder in VS Code: `code ai-health-report-analyzer`.
2. Open the built-in terminal (`` Ctrl+` ``) and initialize git:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: AI Health Report Analyzer"
   ```
3. Create a new **empty** repository on GitHub (no README/license, to avoid
   merge conflicts): https://github.com/new — name it e.g. `ai-health-report-analyzer`.
4. Link and push:
   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/ai-health-report-analyzer.git
   git push -u origin main
   ```
5. If prompted for credentials, use a GitHub **Personal Access Token** (not
   your password): GitHub → Settings → Developer settings → Personal access
   tokens → Generate new token (repo scope) — paste it as the password when
   Git asks.
6. In VS Code, install the **GitHub Pull Requests and Issues** extension (or
   use the built-in Source Control tab) to manage future commits visually —
   stage, commit, and push directly from the sidebar.
7. Copy the repository URL from the GitHub page (`Code` → `HTTPS`) — that's
   your submittable GitHub Repository Link deliverable.

A ready-to-use `.gitignore` is included so `node_modules/`, `venv/`, and
`__pycache__/` are never committed.

## 6. Notes on the RAG / medical knowledge layer

The medical knowledge layer is a curated, source-tagged reference-range table
(`backend/app/reference_ranges.py`) compiled from public WHO / NIH / Mayo
Clinic / ADA / AHA guideline summaries. This is used both as the deterministic
fallback and as the grounding context injected into Claude's prompts — a
lightweight retrieval-augmented-generation pattern that keeps the LLM from
inventing lab values.

## 7. Disclaimer

This tool is for informational purposes only and does not provide medical
diagnoses. Always consult a qualified healthcare professional about abnormal
results.
