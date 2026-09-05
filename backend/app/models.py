"""
Pydantic models shared across the pipeline.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PatientInfo(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    medical_history: Optional[List[str]] = Field(default_factory=list)
    medications: Optional[List[str]] = Field(default_factory=list)
    lifestyle_habits: Optional[List[str]] = Field(default_factory=list)
    symptoms: Optional[List[str]] = Field(default_factory=list)


class BloodParameter(BaseModel):
    name: str
    value: Optional[float] = None
    raw_value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: str = "unknown"  # normal | low | high | critical_low | critical_high | unknown


class ExtractedReport(BaseModel):
    parameters: List[BloodParameter] = Field(default_factory=list)
    report_format_detected: Optional[str] = None
    ocr_confidence: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)


class DeficiencyOrRisk(BaseModel):
    title: str
    parameter: Optional[str] = None
    severity: str = "info"  # info | mild | moderate | severe | critical
    explanation: str


class MedicalAnalysis(BaseModel):
    parameter_explanations: Dict[str, str] = Field(default_factory=dict)
    deficiencies: List[DeficiencyOrRisk] = Field(default_factory=list)
    health_risks: List[DeficiencyOrRisk] = Field(default_factory=list)
    abnormal_parameters: List[str] = Field(default_factory=list)
    sources_consulted: List[str] = Field(default_factory=list)


class Recommendations(BaseModel):
    diet_eat: List[str] = Field(default_factory=list)
    diet_avoid: List[str] = Field(default_factory=list)
    exercise: List[str] = Field(default_factory=list)
    hydration: List[str] = Field(default_factory=list)
    sleep: List[str] = Field(default_factory=list)
    stress_management: List[str] = Field(default_factory=list)
    lifestyle: List[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    overall_health_score: int
    summary: str
    critical_alerts: List[str] = Field(default_factory=list)
    doctor_consultation_suggested: bool = False
    doctor_consultation_reason: Optional[str] = None
    parameters: List[BloodParameter]
    deficiencies: List[DeficiencyOrRisk]
    health_risks: List[DeficiencyOrRisk]
    recommendations: Recommendations
    parameter_explanations: Dict[str, str]


class PipelineState(BaseModel):
    """Shared state object that flows through every LangGraph node."""
    raw_text: str = ""
    file_type: Optional[str] = None
    patient_info: Optional[PatientInfo] = None
    extracted: Optional[ExtractedReport] = None
    analysis: Optional[MedicalAnalysis] = None
    recommendations: Optional[Recommendations] = None
    final_report: Optional[FinalReport] = None
    errors: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class AnalyzeResponse(BaseModel):
    success: bool
    report: Optional[FinalReport] = None
    errors: List[str] = Field(default_factory=list)
