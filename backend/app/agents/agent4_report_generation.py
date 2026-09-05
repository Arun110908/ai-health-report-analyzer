"""
Agent 4 -- Report Generation Agent

Responsibilities:
  - Generate Overall Health Score
  - Create health summary
  - Highlight critical findings
  - (Charts are produced client-side in the React dashboard)
  - Assemble the final downloadable report payload
"""
from app.models import PipelineState, FinalReport, Recommendations


def _compute_health_score(state: PipelineState) -> int:
    params = state.extracted.parameters if state.extracted else []
    if not params:
        return 0
    total = len(params)
    penalty = 0
    for p in params:
        if p.status == "critical_low" or p.status == "critical_high":
            penalty += 15
        elif p.status == "low" or p.status == "high":
            penalty += 7
    score = 100 - min(penalty, 90)
    return max(score, 10)


def run(state: PipelineState) -> PipelineState:
    score = _compute_health_score(state)
    params = state.extracted.parameters if state.extracted else []
    analysis = state.analysis
    recs = state.recommendations

    critical_alerts = []
    for p in params:
        if p.status in ("critical_low", "critical_high"):
            critical_alerts.append(
                f"{p.name} is critically {'low' if 'low' in p.status else 'high'} "
                f"({p.value} {p.unit or ''}) — please consult a doctor promptly."
            )

    doctor_needed = bool(critical_alerts) or (analysis and len(analysis.health_risks) >= 2)
    doctor_reason = None
    if critical_alerts:
        doctor_reason = "One or more parameters are in the critical range."
    elif doctor_needed:
        doctor_reason = "Multiple abnormal parameters detected that warrant professional review."

    abnormal_count = len(analysis.abnormal_parameters) if analysis else 0
    if score >= 85:
        headline = "Your blood report looks largely within healthy ranges."
    elif score >= 60:
        headline = "Your blood report shows a few areas that need attention."
    else:
        headline = "Your blood report shows several abnormal values that need prompt attention."

    summary = (
        f"{headline} Out of {len(params)} parameters analyzed, {abnormal_count} were "
        f"outside the normal reference range. "
        + (f"{len(analysis.deficiencies)} possible deficiency indicator(s) were flagged. " if analysis else "")
        + "This report is for informational purposes only and does not replace professional medical advice."
    )

    state.final_report = FinalReport(
        overall_health_score=score,
        summary=summary,
        critical_alerts=critical_alerts,
        doctor_consultation_suggested=doctor_needed,
        doctor_consultation_reason=doctor_reason,
        parameters=params,
        deficiencies=analysis.deficiencies if analysis else [],
        health_risks=analysis.health_risks if analysis else [],
        recommendations=recs if recs else Recommendations(),
        parameter_explanations=analysis.parameter_explanations if analysis else {},
    )
    return state
