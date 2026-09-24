"""Optional LightGBM + KNN metabolic-risk module.

This is the GlucoSight approach adapted to the report-analyzer pipeline:

1. A separately trained LightGBM model and KNN model receive the same eight
   complete inputs.
2. Their probabilities are averaged (soft voting).
3. SHAP explains the LightGBM side of that estimate feature by feature.

It is deliberately optional. The normal four-agent report analysis still works
without an ML artifact, and this module refuses to impute missing clinical
inputs. The bundled training path uses synthetic data only, so its output is
for an academic demo and must never be presented as a diagnosis.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models import MetabolicRiskPrediction, PipelineState, RiskFeatureContribution
from app.reference_ranges import normalize_parameter_name


FEATURE_ORDER = (
    "age",
    "bmi",
    "blood_pressure",
    "glucose",
    "insulin",
    "cholesterol",
    "hba1c",
    "sugar",
)

FEATURE_LABELS = {
    "age": "Age",
    "bmi": "Body mass index",
    "blood_pressure": "Systolic blood pressure",
    "glucose": "Fasting blood glucose",
    "insulin": "Fasting insulin",
    "cholesterol": "Total cholesterol",
    "hba1c": "HbA1c",
    "sugar": "Post-meal blood glucose",
}

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = BACKEND_DIR / "models" / "metabolic_risk_ensemble.joblib"


def model_path() -> Path:
    """Resolve an explicitly configured artifact path or the project default."""
    return Path(os.getenv("METABOLIC_RISK_MODEL_PATH", str(DEFAULT_MODEL_PATH)))


def _parameter_values(state: PipelineState) -> Dict[str, float]:
    values: Dict[str, float] = {}
    if not state.extracted:
        return values
    for parameter in state.extracted.parameters:
        canonical = normalize_parameter_name(parameter.name)
        if canonical and parameter.value is not None:
            values.setdefault(canonical, float(parameter.value))
    return values


def collect_features(state: PipelineState) -> Tuple[Dict[str, float], List[str]]:
    """Build the exact GlucoSight feature set without inventing missing data."""
    patient = state.patient_info
    report = _parameter_values(state)
    features: Dict[str, float] = {}

    if patient and patient.age is not None:
        features["age"] = float(patient.age)
    if patient and patient.bmi is not None:
        features["bmi"] = float(patient.bmi)
    elif patient and patient.height_cm and patient.weight_kg:
        height_m = float(patient.height_cm) / 100
        if height_m > 0:
            features["bmi"] = round(float(patient.weight_kg) / (height_m * height_m), 2)
    if patient and patient.systolic_bp is not None:
        features["blood_pressure"] = float(patient.systolic_bp)
    if patient and patient.fasting_insulin is not None:
        features["insulin"] = float(patient.fasting_insulin)
    if patient and patient.fasting_glucose is not None:
        features["glucose"] = float(patient.fasting_glucose)
    if patient and patient.total_cholesterol is not None:
        features["cholesterol"] = float(patient.total_cholesterol)
    if patient and patient.hba1c is not None:
        features["hba1c"] = float(patient.hba1c)
    if patient and patient.post_meal_glucose is not None:
        features["sugar"] = float(patient.post_meal_glucose)

    # Parsed report values take precedence over manually supplied optional
    # context: the report is the primary source for this analyzer.
    if "fasting blood glucose" in report:
        features["glucose"] = report["fasting blood glucose"]
    if "postprandial blood glucose" in report:
        features["sugar"] = report["postprandial blood glucose"]
    if "total cholesterol" in report:
        features["cholesterol"] = report["total cholesterol"]
    if "hba1c" in report:
        features["hba1c"] = report["hba1c"]

    missing = [FEATURE_LABELS[key] for key in FEATURE_ORDER if key not in features]
    return features, missing


def _prediction(status: str, message: str, **extra) -> MetabolicRiskPrediction:
    return MetabolicRiskPrediction(status=status, message=message, **extra)


def _positive_class_shap_values(shap_values):
    """Normalise SHAP's version-dependent binary-class output shape."""
    import numpy as np

    if isinstance(shap_values, list):
        return np.asarray(shap_values[-1])[0]
    values = np.asarray(shap_values)
    if values.ndim == 3:  # newer SHAP: samples × features × classes
        return values[0, :, -1]
    if values.ndim == 2:
        return values[0]
    return values.reshape(-1)


def _load_artifact(path: Path):
    """Load locally; the project never uploads or persists patient inputs."""
    import joblib

    artifact = joblib.load(path)
    required = {"scaler", "lgbm_model", "knn_model", "feature_order", "model_id"}
    missing = required.difference(artifact)
    if missing:
        raise ValueError(f"artifact is missing: {', '.join(sorted(missing))}")
    if tuple(artifact["feature_order"]) != FEATURE_ORDER:
        raise ValueError("artifact feature order does not match this project")
    return artifact


def predict_metabolic_risk(state: PipelineState) -> MetabolicRiskPrediction:
    """Return an explained soft-voting estimate when all safe prerequisites hold."""
    path = model_path()
    if not path.exists():
        return _prediction(
            "model_not_trained",
            "The optional ML model is not trained yet. Run the documented demo training command first.",
        )

    features, missing = collect_features(state)
    if missing:
        return _prediction(
            "insufficient_data",
            "The report analysis is complete, but the ML demo needs every listed input and will not guess missing values.",
            missing_features=missing,
        )

    try:
        import numpy as np
        import shap

        artifact = _load_artifact(path)
        ordered = np.array([[features[key] for key in FEATURE_ORDER]], dtype=float)
        scaled = artifact["scaler"].transform(ordered)
        lgbm_probability = float(artifact["lgbm_model"].predict_proba(scaled)[0][1])
        knn_probability = float(artifact["knn_model"].predict_proba(scaled)[0][1])
        score = (lgbm_probability + knn_probability) / 2
        agreement = 1 - abs(lgbm_probability - knn_probability)

        if score < 0.33:
            band = "Low"
        elif score < 0.66:
            band = "Moderate"
        else:
            band = "High"

        explainer = shap.TreeExplainer(artifact["lgbm_model"])
        shap_values = _positive_class_shap_values(explainer.shap_values(scaled))
        contributors = [
            RiskFeatureContribution(
                feature=key,
                display_name=FEATURE_LABELS[key],
                value=features[key],
                shap_contribution=round(float(shap_values[index]), 5),
            )
            for index, key in enumerate(FEATURE_ORDER)
        ]
        contributors.sort(key=lambda item: abs(item.shap_contribution), reverse=True)

        return _prediction(
            "available",
            "Optional LightGBM + KNN demo estimate. Review the contribution direction alongside the non-diagnostic disclaimer.",
            risk_score=round(score, 4),
            risk_band=band,
            model_id=str(artifact["model_id"]),
            model_agreement=round(agreement, 4),
            top_contributors=contributors[:5],
        )
    except Exception:
        # Do not expose library paths or model internals in a health response.
        return _prediction(
            "unavailable",
            "The optional ML estimate could not run. The rule-based report analysis is still available.",
        )


def risk_model_status() -> dict:
    """Small, non-sensitive status payload for the API and the dashboard."""
    path = model_path()
    return {
        "enabled": path.exists(),
        "feature_labels": [FEATURE_LABELS[key] for key in FEATURE_ORDER],
        "training_data_note": "The bundled training script generates synthetic academic-demo data only.",
    }
