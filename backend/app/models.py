"""
Pydantic models shared across the pipeline.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class PatientInfo(BaseModel):
    age: Optional[int] = Field(default=None, ge=1, le=120)
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    medical_history: Optional[List[str]] = Field(default_factory=list)
    medications: Optional[List[str]] = Field(default_factory=list)
    lifestyle_habits: Optional[List[str]] = Field(default_factory=list)
    symptoms: Optional[List[str]] = Field(default_factory=list)
    # Optional inputs for the academic LightGBM + KNN metabolic-risk demo.
    # They are never persisted and are not needed for normal report analysis.
    systolic_bp: Optional[float] = Field(default=None, ge=60, le=250)
    fasting_insulin: Optional[float] = Field(default=None, ge=0, le=900)
    bmi: Optional[float] = Field(default=None, ge=10, le=70)
    fasting_glucose: Optional[float] = Field(default=None, ge=40, le=500)
    total_cholesterol: Optional[float] = Field(default=None, ge=80, le=500)
    hba1c: Optional[float] = Field(default=None, ge=3, le=18)
    post_meal_glucose: Optional[float] = Field(default=None, ge=40, le=500)


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


class RiskFeatureContribution(BaseModel):
    feature: str
    display_name: str
    value: float
    shap_contribution: float


class MetabolicRiskPrediction(BaseModel):
    """Optional, non-diagnostic output from the LightGBM + KNN ensemble."""
    model_config = ConfigDict(protected_namespaces=())
    status: str  # available | model_not_trained | insufficient_data | unavailable
    message: str
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    model_id: Optional[str] = None
    model_agreement: Optional[float] = None
    missing_features: List[str] = Field(default_factory=list)
    top_contributors: List[RiskFeatureContribution] = Field(default_factory=list)
    disclaimer: str = (
        "Academic decision-support demonstration only. This score is not a diagnosis, "
        "screening result, or treatment recommendation."
    )


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
    metabolic_risk: Optional[MetabolicRiskPrediction] = None


class PipelineState(BaseModel):
    """Shared state object that flows through every LangGraph node."""
    raw_text: str = ""
    file_type: Optional[str] = None
    ocr_confidence: float = 1.0   # 1.0 for text/native-PDF/DOCX; Tesseract mean confidence for scans
    patient_info: Optional[PatientInfo] = None
    extracted: Optional[ExtractedReport] = None
    analysis: Optional[MedicalAnalysis] = None
    recommendations: Optional[Recommendations] = None
    metabolic_risk: Optional[MetabolicRiskPrediction] = None
    final_report: Optional[FinalReport] = None
    errors: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class AnalyzeResponse(BaseModel):
    success: bool
    report: Optional[FinalReport] = None
    errors: List[str] = Field(default_factory=list)
