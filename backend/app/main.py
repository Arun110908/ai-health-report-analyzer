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
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import PipelineState, PatientInfo, AnalyzeResponse
from app.pipeline import run_pipeline, using_langgraph
from app.llm_client import claude_client
from app.ocr_extraction import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
)

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
    }


def _extract_bytes(filename: str, content: bytes) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "pdf":
        text, _conf = extract_text_from_pdf(content)
    elif suffix in ("jpg", "jpeg", "png"):
        text, _conf = extract_text_from_image(content)
    elif suffix == "docx":
        text, _conf = extract_text_from_docx(content)
    elif suffix in ("txt",):
        text = content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{suffix}")
    return text


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
    text = _extract_bytes(file.filename, content)

    state = PipelineState(raw_text=text, file_type=file.filename.split(".")[-1].lower(),
                           patient_info=_parse_patient_info(patient_info))
    state = run_pipeline(state)

    if not state.final_report:
        return AnalyzeResponse(success=False, errors=state.errors or ["Pipeline failed to produce a report."])
    return AnalyzeResponse(success=True, report=state.final_report, errors=state.errors)


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
def analyze_sample(sample_name: str):
    path = SAMPLE_DIR / sample_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sample report not found.")
    text = path.read_text()
    state = PipelineState(raw_text=text, file_type="text")
    state = run_pipeline(state)
    if not state.final_report:
        return AnalyzeResponse(success=False, errors=state.errors or ["Pipeline failed to produce a report."])
    return AnalyzeResponse(success=True, report=state.final_report, errors=state.errors)
