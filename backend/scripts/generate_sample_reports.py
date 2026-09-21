"""
Generates synthetic blood-report .txt files WITH GROUND TRUTH so accuracy can
be measured (scripts/evaluate.py). Run:

    python scripts/generate_sample_reports.py

What makes these harder / more realistic than a single 'Name: value unit (range)' layout:
  * 4 genuinely different layouts (colon list, spaced table, pipe table with
    H/L flag column, Indian-lab style)
  * abbreviations / alternate test names (Hb, TLC, FBS, Vit D 25-OH, SGPT (ALT) ...)
  * unit variants (WBC as 6,500 cells/cumm, platelets as 2.5 lakhs/cumm)
  * sex-specific ranges (haemoglobin 13-17 for men, 12-15 for women)
  * multi-band lipid ranges ('Desirable <200 Borderline 200-239 High >=240')
  * noise lines (patient name, age/sex, dates, page numbers) that must NOT
    be extracted as parameters
  * values are never negative (the old generator could emit -193 pg/mL)

Ground truth is written to sample_data/ground_truth.json:
  { file: { layout, sex, params: { canonical_name: {value, status} } } }
value is in the standard (table) unit; status is low/normal/high vs the range
that is PRINTED on the report (or the built-in table where the report prints
an ambiguous multi-band range).
"""
import json
import random
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).resolve().parent.parent / "sample_data"
OUT_DIR.mkdir(exist_ok=True)

# canonical, (low, high), std unit, {layout: printed name}
P = [
    ("hemoglobin", (13.0, 17.0), "g/dL", {0: "Hemoglobin", 1: "Haemoglobin", 2: "Hb", 3: "Haemoglobin (Hb)"}),
    ("wbc count", (4.0, 11.0), "10^3/uL", {0: "WBC Count", 1: "Total WBC Count", 2: "TLC", 3: "Total Leucocyte Count (TLC)"}),
    ("platelet count", (150, 450), "10^3/uL", {0: "Platelet Count", 1: "Platelet Count", 2: "Platelets", 3: "Platelet Count"}),
    ("fasting blood glucose", (70, 99), "mg/dL", {0: "Fasting Blood Glucose", 1: "Glucose Fasting", 2: "FBS", 3: "Fasting Blood Sugar (FBS)"}),
    ("hba1c", (4.0, 5.6), "%", {0: "HbA1c", 1: "Glycosylated Hemoglobin (HbA1c)", 2: "HbA1c", 3: "HbA1c"}),
    ("total cholesterol", (120, 200), "mg/dL", {0: "Total Cholesterol", 1: "Cholesterol Total", 2: "Cholesterol", 3: "Total Cholesterol"}),
    ("ldl cholesterol", (50, 100), "mg/dL", {0: "LDL Cholesterol", 1: "LDL Cholesterol", 2: "LDL", 3: "LDL Cholesterol"}),
    ("hdl cholesterol", (40, 60), "mg/dL", {0: "HDL Cholesterol", 1: "HDL Cholesterol", 2: "HDL", 3: "HDL Cholesterol"}),
    ("triglycerides", (50, 150), "mg/dL", {0: "Triglycerides", 1: "Triglycerides", 2: "TG", 3: "Triglycerides"}),
    ("tsh", (0.4, 4.0), "uIU/mL", {0: "TSH", 1: "TSH (Ultrasensitive)", 2: "TSH", 3: "Thyroid Stimulating Hormone (TSH)"}),
    ("vitamin d", (30, 100), "ng/mL", {0: "Vitamin D", 1: "Vitamin D, 25 Hydroxy", 2: "Vit D 25-OH", 3: "25-Hydroxy Vitamin D"}),
    ("vitamin b12", (200, 900), "pg/mL", {0: "Vitamin B12", 1: "Vitamin B12", 2: "B12", 3: "Vitamin B12"}),
    ("serum creatinine", (0.6, 1.3), "mg/dL", {0: "Serum Creatinine", 1: "Creatinine", 2: "Creatinine", 3: "Serum Creatinine"}),
    ("sgpt", (7, 56), "U/L", {0: "SGPT", 1: "SGPT (ALT)", 2: "ALT", 3: "SGPT/ALT"}),
    ("calcium", (8.6, 10.3), "mg/dL", {0: "Calcium", 1: "Calcium", 2: "Calcium", 3: "Serum Calcium"}),
]
TABLE_RANGE_FOR_MULTIBAND = {"total cholesterol": (0, 200)}  # what Agent 1 falls back to

NAMES = ["Ravi Kumar", "Priya Lakshmi", "Arjun Das", "Meena Sundaram", "Karthik R", "Divya Nair"]
LAB_HEADERS = [
    "APEX DIAGNOSTIC LABORATORIES\nComplete Blood Chemistry Report",
    "CITY CARE PATHOLOGY LAB\nBlood Investigation Report",
    "SUNRISE MEDICAL CENTRE\nLaboratory Test Report",
    "METRO HEALTH DIAGNOSTICS\nBiochemistry & Hematology Panel",
]


def status_of(v, lo, hi):
    return "low" if v < lo else "high" if v > hi else "normal"


def gen_value(lo, hi, abnormal):
    span = hi - lo
    if abnormal:
        if random.random() < 0.5:
            v = lo - span * random.uniform(0.1, 0.6)
            v = max(v, lo * 0.15 if lo > 0 else 0.05)   # never negative / absurd
        else:
            v = hi + span * random.uniform(0.1, 0.6)
    else:
        v = random.uniform(lo, hi)
    return round(v, 2)


def fmt(x):
    return f"{x:g}"


def make_report(idx: int):
    layout = idx % 4
    sex = "Female" if idx % 2 == 0 else "Male"
    truth = {}
    rows = []
    abnormal_report = idx % 3 == 0
    for canonical, (lo, hi), unit, names in P:
        r_lo, r_hi = (12.0, 15.0) if (canonical == "hemoglobin" and sex == "Female") else (lo, hi)
        v = gen_value(r_lo, r_hi, abnormal_report and random.random() < 0.35)
        name = names[layout]
        multiband = layout == 3 and canonical == "total cholesterol"
        if multiband:
            truth_status = status_of(v, *TABLE_RANGE_FOR_MULTIBAND[canonical])
        else:
            truth_status = status_of(v, r_lo, r_hi)
        truth[canonical] = {"value": v, "status": truth_status}
        rows.append((canonical, name, v, unit, r_lo, r_hi, truth_status, multiband))

    hdr = random.choice(LAB_HEADERS)
    pname = random.choice(NAMES)
    lines = [hdr, f"Patient Name: {pname}", f"Age: {random.randint(21, 68)} Years   Sex: {sex}",
             f"Sample Collected: {random.randint(1, 28):02d}/09/2025 08:{random.randint(10, 59)}",
             f"Report Format Variant: {layout}", "-" * 60]
    if layout == 1:
        lines.append(f"{'TEST NAME':<34}{'RESULT':>10}  {'UNIT':<10}REFERENCE RANGE")
    if layout == 2:
        lines.append("| Test | Result | Unit | Ref. Range | Flag |")
    for canonical, name, v, unit, lo, hi, st, multiband in rows:
        flag = {"low": "L", "high": "H", "normal": ""}[st]
        if layout == 0:
            lines.append(f"{name}: {v} {unit} ({fmt(lo)}-{fmt(hi)})")
        elif layout == 1:
            lines.append(f"{name:<34}{v:>10}  {unit:<10}{fmt(lo)} - {fmt(hi)}")
        elif layout == 2:
            lines.append(f"| {name} | {v} | {unit} | {fmt(lo)} - {fmt(hi)} | {flag} |")
        else:
            if canonical == "wbc count":
                lines.append(f"{name:<32}{int(round(v * 1000)):,}  cells/cumm   {int(lo * 1000):,} - {int(hi * 1000):,}  {flag}")
            elif canonical == "platelet count":
                lines.append(f"{name:<32}{round(v / 100, 2)}  lakhs/cumm   {lo / 100:g} - {hi / 100:g}  {flag}")
            elif multiband:
                lines.append(f"{name:<32}{v}  mg/dL   Desirable: <200  Borderline: 200-239  High: >=240")
            elif canonical == "hemoglobin":
                lines.append(f"{name:<32}{v}  g/dL   Male: 13.0-17.0  Female: 12.0-15.0" if idx % 8 == 0
                             else f"{name:<32}{v}  g/dL   {fmt(lo)} - {fmt(hi)}  {flag}")
            else:
                lines.append(f"{name:<32}{v}  {unit}   Ref: {fmt(lo)} - {fmt(hi)}  {flag}")
    lines += ["-" * 60, "Method: Photometry / Automated analyser", "Page 1 of 1", "*** End of Report ***"]
    # hemoglobin with ambiguous male/female band: truth uses the built-in (male) table range
    if layout == 3 and idx % 8 == 0:
        v = truth["hemoglobin"]["value"]
        truth["hemoglobin"]["status"] = status_of(v, 13.0, 17.0)
    return "\n".join(lines), {"layout": layout, "sex": sex, "params": truth}


def main():
    count = 25
    gt = {}
    for i in range(1, count + 1):
        text, meta = make_report(i)
        name = f"sample_report_{i:02d}.txt"
        (OUT_DIR / name).write_text(text)
        gt[name] = meta
    (OUT_DIR / "ground_truth.json").write_text(json.dumps(gt, indent=1))
    print(f"Generated {count} synthetic sample reports + ground_truth.json in {OUT_DIR}")


if __name__ == "__main__":
    main()
