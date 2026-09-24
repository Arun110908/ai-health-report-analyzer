# Optional ML risk module

The project now includes the same technical pattern used in GlucoSight:

```text
complete 8-feature input
       │
       ├── StandardScaler → LightGBM → probability ┐
       └── StandardScaler → KNN      → probability ├─ average → risk band
                                                    │
                                        SHAP ← LightGBM
```

It is an academic demonstration only. The provided generator creates synthetic
data, so its metrics describe that synthetic hold-out set, not people or
clinical validity.

## Create the local demo artifact

```bash
cd backend
python scripts/generate_demo_risk_data.py --rows 600
python scripts/train_risk_model.py --input data/demo_metabolic_risk.csv
```

This creates `backend/models/metabolic_risk_ensemble.joblib`. It is excluded
from Git because it is generated locally. The normal report analyzer works even
when the artifact is absent.

The production Docker image performs those same two commands during its build,
using this synthetic dataset only. This lets the deployed dashboard demonstrate
the LightGBM + KNN soft vote and LightGBM SHAP contributions without committing
a generated model file to the repository. Set Docker build argument
`TRAIN_DEMO_RISK_MODEL=false` to leave the optional demo inactive.

## Safe integration rules

- The model never receives partial data: it reports every missing input instead
  of filling it with an average.
- Inputs and prediction results are not written to disk by this module.
- The API includes a non-diagnostic disclaimer in every ML result.
- SHAP explains the LightGBM contribution only; it does not turn the ensemble
  into a medical explanation or causal finding.
- Replace the synthetic dataset only after appropriate approval, validation,
  bias analysis, and clinical review.
