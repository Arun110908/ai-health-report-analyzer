"""Generate a clearly labelled synthetic dataset for the ML demo.

It exists only to demonstrate the training, soft-voting, and SHAP plumbing.
Do not describe the resulting model as clinically validated and do not use it
for patient care. A real deployment needs an approved, representative dataset,
governance, validation, and clinical review.
"""
import argparse
from pathlib import Path


FEATURE_ORDER = (
    "age", "bmi", "blood_pressure", "glucose",
    "insulin", "cholesterol", "hba1c", "sugar",
)


def generate(rows: int, seed: int):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    age = rng.normal(50, 14, rows).clip(18, 90)
    bmi = rng.normal(28, 6, rows).clip(15, 55)
    blood_pressure = rng.normal(125, 15, rows).clip(80, 200)
    glucose = rng.normal(120, 35, rows).clip(60, 300)
    insulin = rng.normal(90, 40, rows).clip(5, 400)
    cholesterol = rng.normal(200, 35, rows).clip(100, 350)
    hba1c = rng.normal(5.8, 1.1, rows).clip(4.0, 12.0)
    sugar = rng.normal(110, 30, rows).clip(60, 300)

    # An intentionally transparent synthetic label, with a little noise so
    # the training code has a non-trivial binary target to learn.
    signal = (
        0.03 * (glucose - 100)
        + 0.50 * (hba1c - 5.5)
        + 0.02 * (bmi - 25)
        + 0.015 * (age - 40)
        + 0.010 * (blood_pressure - 120)
        + rng.normal(0, 1.2, rows)
    )
    risk = (signal > np.percentile(signal, 55)).astype(int)
    return pd.DataFrame({
        "age": age.round(1), "bmi": bmi.round(1),
        "blood_pressure": blood_pressure.round(1), "glucose": glucose.round(1),
        "insulin": insulin.round(1), "cholesterol": cholesterol.round(1),
        "hba1c": hba1c.round(2), "sugar": sugar.round(1), "risk": risk,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/demo_metabolic_risk.csv")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataset = generate(args.rows, args.seed)
    dataset.to_csv(output, index=False)
    print(f"Wrote {len(dataset)} synthetic rows to {output}")
    print("Class balance:", dataset["risk"].value_counts().to_dict())
