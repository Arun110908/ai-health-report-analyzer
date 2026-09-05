"""
Generates >=20 synthetic blood-report .txt files covering normal and
abnormal cases, multiple "lab formats", to satisfy the project's
Dataset Usage & Testing requirement. Run:

    python scripts/generate_sample_reports.py
"""
import random
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).resolve().parent.parent / "sample_data"
OUT_DIR.mkdir(exist_ok=True)

PARAMS = [
    ("Hemoglobin", 13.0, 17.0, "g/dL"),
    ("WBC Count", 4.0, 11.0, "10^3/uL"),
    ("Platelet Count", 150, 450, "10^3/uL"),
    ("Fasting Blood Glucose", 70, 99, "mg/dL"),
    ("HbA1c", 4.0, 5.6, "%"),
    ("Total Cholesterol", 120, 200, "mg/dL"),
    ("LDL Cholesterol", 50, 100, "mg/dL"),
    ("HDL Cholesterol", 40, 60, "mg/dL"),
    ("Triglycerides", 50, 150, "mg/dL"),
    ("TSH", 0.4, 4.0, "uIU/mL"),
    ("Vitamin D", 30, 100, "ng/mL"),
    ("Vitamin B12", 200, 900, "pg/mL"),
    ("Serum Creatinine", 0.6, 1.3, "mg/dL"),
    ("SGPT", 7, 56, "U/L"),
    ("Calcium", 8.6, 10.3, "mg/dL"),
]

LAB_HEADERS = [
    "APEX DIAGNOSTIC LABORATORIES\nComplete Blood Chemistry Report\n",
    "CITY CARE PATHOLOGY LAB\nBlood Investigation Report\n",
    "SUNRISE MEDICAL CENTRE\nLaboratory Test Report\n",
    "METRO HEALTH DIAGNOSTICS\nBiochemistry & Hematology Panel\n",
]


def make_report(idx: int, abnormal_bias: bool) -> str:
    header = random.choice(LAB_HEADERS)
    lines = [header, f"Patient ID: SAMPLE-{idx:03d}", f"Report Format Variant: {idx % 4}", "-" * 40]
    for name, low, high, unit in PARAMS:
        if abnormal_bias and random.random() < 0.35:
            # push value outside range
            if random.random() < 0.5:
                value = round(low - (high - low) * random.uniform(0.1, 0.6), 2)
            else:
                value = round(high + (high - low) * random.uniform(0.1, 0.6), 2)
        else:
            value = round(random.uniform(low, high), 2)
        lines.append(f"{name}: {value} {unit} ({low}-{high})")
    return "\n".join(lines)


def main():
    count = 25
    for i in range(1, count + 1):
        abnormal = i % 3 == 0  # roughly 1/3 of reports have abnormal values
        text = make_report(i, abnormal_bias=abnormal)
        (OUT_DIR / f"sample_report_{i:02d}.txt").write_text(text)
    print(f"Generated {count} synthetic sample reports in {OUT_DIR}")


if __name__ == "__main__":
    main()
