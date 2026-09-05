"""
Agent 3 -- Recommendation Agent

Responsibilities:
  - Generate personalized diet recommendations (foods to eat/avoid)
  - Recommend exercise plans
  - Provide sleep recommendations
  - Suggest stress management techniques
  - Offer healthy lifestyle improvements
"""
from app.models import PipelineState, Recommendations
from app.reference_ranges import normalize_parameter_name
from app.llm_client import claude_client

FOOD_MAP = {
    "hemoglobin": {"eat": ["Spinach and leafy greens", "Red meat or legumes", "Vitamin C-rich fruits to aid iron absorption"],
                   "avoid": ["Excess tea/coffee with meals (inhibits iron absorption)"]},
    "vitamin d": {"eat": ["Fatty fish (salmon, mackerel)", "Fortified milk/cereal", "10-15 min sunlight exposure daily"],
                  "avoid": []},
    "vitamin b12": {"eat": ["Eggs, dairy, fortified cereals", "Meat/fish if non-vegetarian"], "avoid": []},
    "fasting blood glucose": {"eat": ["Whole grains, fiber-rich vegetables", "Lean protein"],
                               "avoid": ["Refined sugar and sugary drinks", "White bread/rice in excess"]},
    "hba1c": {"eat": ["Low-glycemic-index foods", "High-fiber vegetables"],
              "avoid": ["Sweets, sugary beverages"]},
    "ldl cholesterol": {"eat": ["Oats, nuts, olive oil", "Fruits and vegetables"],
                         "avoid": ["Fried foods", "Trans fats / processed snacks"]},
    "triglycerides": {"eat": ["Omega-3 rich fish", "Whole grains"], "avoid": ["Alcohol", "Sugary foods"]},
    "serum creatinine": {"eat": ["Stay well hydrated", "Balanced protein intake"],
                          "avoid": ["Excess protein/salt without medical guidance"]},
}

DEFAULT_LIFESTYLE = [
    "Get a routine annual health check-up.",
    "Maintain a consistent sleep and wake schedule.",
    "Include at least 30 minutes of physical activity most days of the week.",
]


def _rule_based_recommendations(state: PipelineState) -> Recommendations:
    eat, avoid, exercise, hydration, sleep, stress, lifestyle = [], [], [], [], [], [], list(DEFAULT_LIFESTYLE)

    abnormal_names = set(state.analysis.abnormal_parameters) if state.analysis else set()
    any_cardio_flag = False
    any_glucose_flag = False

    for p in state.extracted.parameters:
        canonical = normalize_parameter_name(p.name)
        if p.name in abnormal_names and canonical in FOOD_MAP:
            eat.extend(FOOD_MAP[canonical]["eat"])
            avoid.extend(FOOD_MAP[canonical]["avoid"])
        if canonical in ("ldl cholesterol", "triglycerides", "total cholesterol"):
            any_cardio_flag = any_cardio_flag or p.name in abnormal_names
        if canonical in ("fasting blood glucose", "hba1c"):
            any_glucose_flag = any_glucose_flag or p.name in abnormal_names

    if any_cardio_flag:
        exercise.append("30 minutes of brisk walking / cardio, 5 days a week (consult your doctor first).")
    if any_glucose_flag:
        exercise.append("Post-meal 10-15 minute walks to help regulate blood sugar.")
    if not exercise:
        exercise.append("150 minutes/week of moderate exercise (walking, cycling, swimming).")

    hydration.append("Drink at least 2-3 liters of water daily unless advised otherwise.")
    sleep.append("Aim for 7-8 hours of quality sleep each night, with a consistent bedtime.")
    stress.append("Practice 10 minutes of deep breathing, meditation, or yoga daily.")
    stress.append("Take regular breaks from screens and prioritize downtime.")

    # de-duplicate while preserving order
    def dedup(lst):
        seen = set()
        out = []
        for x in lst:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return Recommendations(
        diet_eat=dedup(eat) or ["Maintain a balanced diet rich in fruits, vegetables, and whole grains."],
        diet_avoid=dedup(avoid) or ["Limit ultra-processed foods and excess sugar/salt."],
        exercise=dedup(exercise),
        hydration=dedup(hydration),
        sleep=dedup(sleep),
        stress_management=dedup(stress),
        lifestyle=dedup(lifestyle),
    )


def run(state: PipelineState) -> PipelineState:
    if not state.extracted or not state.extracted.parameters:
        state.recommendations = Recommendations()
        return state

    if claude_client.available and state.analysis:
        system = (
            "You are a wellness assistant. Based on the abnormal blood parameters and "
            "deficiencies provided, generate practical, safe, general-population lifestyle "
            "recommendations (never dosages or prescriptions). Return ONLY valid JSON matching: "
            "{\"diet_eat\":[str], \"diet_avoid\":[str], \"exercise\":[str], \"hydration\":[str], "
            "\"sleep\":[str], \"stress_management\":[str], \"lifestyle\":[str]}"
        )
        user = (
            f"Abnormal parameters: {state.analysis.abnormal_parameters}\n"
            f"Deficiencies: {[d.title for d in state.analysis.deficiencies]}\n"
            f"Health risks: {[r.title for r in state.analysis.health_risks]}"
        )
        result = claude_client.complete_json(system, user)
        if result:
            try:
                state.recommendations = Recommendations(**result)
                return state
            except Exception:  # noqa: BLE001
                pass

    state.recommendations = _rule_based_recommendations(state)
    return state
