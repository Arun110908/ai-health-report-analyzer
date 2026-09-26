"""
AI Health Report Analyzer & Personal Health Assistant -- FastAPI backend.

Endpoints:
  GET  /health                 -> liveness probe
  GET  /api/status             -> pipeline mode (LangGraph vs fallback, LLM on/off)
  POST /api/analyze            -> upload a report (PDF/DOCX/JPG/PNG) + optional
                                   patient info, returns the full FinalReport JSON
  POST /api/analyze-text       -> analyze raw pasted report text (handy for demos
                                   / grading without needing a real file)
  GET  /api/sample-reports     -> list bundled synthetic sample reports
  POST /api/analyze-sample/{id}-> run the pipeline on a bundled sample report
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from typing import List
from app.models import PipelineState, PatientInfo, AnalyzeResponse, BatchAnalyzeResponse, BatchReportItem
from app.pipeline import run_pipeline, using_langgraph
from app.llm_client import claude_client
from app.ocr_extraction import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
)
from app.ml_risk import risk_model_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Health Report Analyzer & Personal Health Assistant",
    description="Multi-agent pipeline that turns raw blood reports into a personalized health summary.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return {
        "pipeline_engine": "langgraph" if using_langgraph() else "sequential-fallback",
        "llm_enabled": claude_client.available,
        "agents": [
            "Agent 1 - Report Processing",
            "Agent 2 - Medical Analysis",
            "Agent 3 - Recommendation",
            "Agent 4 - Report Generation",
        ],
        "ml_risk": risk_model_status(),
    }


@app.get("/api/risk-model/status")
def risk_status():
    """Report whether the optional LightGBM + KNN artifact is ready."""
    return risk_model_status()


def _extract_bytes(filename: str, content: bytes):
    """Returns (text, ocr_confidence)."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    conf = 1.0
    if suffix == "pdf":
        text, conf = extract_text_from_pdf(content)
    elif suffix in ("jpg", "jpeg", "png"):
        text, conf = extract_text_from_image(content)
    elif suffix == "docx":
        text, conf = extract_text_from_docx(content)
    elif suffix in ("txt",):
        text = content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{suffix}")
    return text, conf


def _parse_patient_info(patient_info_json: Optional[str]) -> Optional[PatientInfo]:
    if not patient_info_json:
        return None
    try:
        return PatientInfo(**json.loads(patient_info_json))
    except Exception:  # noqa: BLE001
        return None


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...), patient_info: Optional[str] = Form(None)):
    content = await file.read()
    text, conf = _extract_bytes(file.filename, content)

    state = PipelineState(raw_text=text, ocr_confidence=conf,
                          file_type=file.filename.split(".")[-1].lower(),
                           patient_info=_parse_patient_info(patient_info))
    state = run_pipeline(state)

    if not state.final_report:
        return AnalyzeResponse(success=False, errors=state.errors or ["Pipeline failed to produce a report."])
    return AnalyzeResponse(success=True, report=state.final_report, errors=state.errors)


MAX_BATCH_FILES = 10


@app.post("/api/analyze-batch", response_model=BatchAnalyzeResponse)
async def analyze_batch(files: List[UploadFile] = File(...), patient_info: Optional[str] = Form(None)):
    """Analyze several reports (PDF/DOCX/JPG/PNG) in one call, each run through
    the same 4-agent pipeline independently. A failure on one file (bad
    format, empty scan) never blocks the others -- each row reports its own
    success/errors so the caller can show a per-file result list."""
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"Send at most {MAX_BATCH_FILES} files per batch.")

    shared_patient_info = _parse_patient_info(patient_info)
    results: List[BatchReportItem] = []
    for f in files:
        try:
            content = await f.read()
            text, conf = _extract_bytes(f.filename, content)
            state = PipelineState(raw_text=text, ocr_confidence=conf,
                                  file_type=f.filename.split(".")[-1].lower(),
                                  patient_info=shared_patient_info)
            state = run_pipeline(state)
            if not state.final_report:
                results.append(BatchReportItem(filename=f.filename, success=False,
                               errors=state.errors or ["Pipeline failed to produce a report."]))
            else:
                results.append(BatchReportItem(filename=f.filename, success=True,
                               report=state.final_report, errors=state.errors))
        except Exception as e:  # noqa: BLE001
            logger.exception("Batch item failed: %s", f.filename)
            results.append(BatchReportItem(filename=f.filename, success=False,
                           errors=[f"Could not process this file: {e}"]))
    return BatchAnalyzeResponse(results=results)


@app.post("/api/analyze-text", response_model=AnalyzeResponse)
async def analyze_text(report_text: str = Form(...), patient_info: Optional[str] = Form(None)):
    state = PipelineState(raw_text=report_text, file_type="text",
                           patient_info=_parse_patient_info(patient_info))
    state = run_pipeline(state)

    if not state.final_report:
        return AnalyzeResponse(success=False, errors=state.errors or ["Pipeline failed to produce a report."])
    return AnalyzeResponse(success=True, report=state.final_report, errors=state.errors)


@app.get("/api/sample-reports")
def list_sample_reports():
    if not SAMPLE_DIR.exists():
        return {"samples": []}
    return {"samples": sorted(p.name for p in SAMPLE_DIR.glob("*.txt"))}


@app.post("/api/analyze-sample/{sample_name}", response_model=AnalyzeResponse)
def analyze_sample(sample_name: str, patient_info: Optional[str] = Form(None)):
    path = SAMPLE_DIR / sample_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sample report not found.")
    text = path.read_text()
    state = PipelineState(raw_text=text, file_type="text", patient_info=_parse_patient_info(patient_info))
    state = run_pipeline(state)
    if not state.final_report:
        return AnalyzeResponse(success=False, errors=state.errors or ["Pipeline failed to produce a report."])
    return AnalyzeResponse(success=True, report=state.final_report, errors=state.errors)


# The Vite development server handles the frontend during local development.
# A production Docker image sets STATIC_DIR to its compiled React assets so the
# API and dashboard can be deployed together as one service.
STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static"))
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
