"""Train the optional LightGBM + KNN soft-voting demo artifact.

Input CSV columns must match FEATURE_ORDER and the target must be a binary
0/1 column. The default data generator is synthetic; replace it only with a
properly approved and validated dataset before any non-academic use.
"""
import argparse
import datetime as dt
from pathlib import Path

from generate_demo_risk_data import FEATURE_ORDER


def load_data(path: Path, target: str):
    import pandas as pd

    data = pd.read_csv(path).dropna()
    missing = set(FEATURE_ORDER).difference(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing feature columns: {', '.join(sorted(missing))}")
    if target not in data:
        raise ValueError(f"Dataset is missing target column: {target}")
    if not set(data[target].unique()).issubset({0, 1}):
        raise ValueError("Target must contain binary 0/1 labels.")
    return data[list(FEATURE_ORDER)], data[target]


def train(input_path: Path, target: str, output_path: Path, iterations: int):
    import joblib
    from lightgbm import LGBMClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import RandomizedSearchCV, train_test_split
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.preprocessing import StandardScaler

    features, labels = load_data(input_path, target)
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    search = RandomizedSearchCV(
        LGBMClassifier(objective="binary", random_state=42, verbosity=-1),
        param_distributions={
            "n_estimators": [100, 200, 300], "num_leaves": [15, 31, 63],
            "learning_rate": [0.01, 0.03, 0.05, 0.1], "max_depth": [-1, 4, 6, 8],
            "min_child_samples": [5, 10, 20], "subsample": [0.7, 0.85, 1.0],
            "colsample_bytree": [0.7, 0.85, 1.0],
        },
        n_iter=max(1, iterations), scoring="roc_auc", cv=3, random_state=42, n_jobs=-1,
    )
    search.fit(x_train_scaled, y_train)
    lightgbm = search.best_estimator_

    knn = KNeighborsClassifier(n_neighbors=7, weights="distance")
    knn.fit(x_train_scaled, y_train)
    lightgbm_probability = lightgbm.predict_proba(x_test_scaled)[:, 1]
    knn_probability = knn.predict_proba(x_test_scaled)[:, 1]
    probability = (lightgbm_probability + knn_probability) / 2
    prediction = (probability >= 0.5).astype(int)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, prediction)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probability)), 4),
    }

    artifact = {
        "scaler": scaler, "lgbm_model": lightgbm, "knn_model": knn,
        "feature_order": FEATURE_ORDER,
        "model_id": "metabolic-demo-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "metrics": metrics,
        "training_data_note": "Synthetic academic-demo data; not clinically validated.",
        "best_lightgbm_params": search.best_params_,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path)
    print(f"Saved {output_path} ({artifact['model_id']})")
    print("Hold-out metrics on the supplied dataset:", metrics)
    print("Important: these metrics are not clinical validation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/demo_metabolic_risk.csv")
    parser.add_argument("--target", default="risk")
    parser.add_argument("--output", default="models/metabolic_risk_ensemble.joblib")
    parser.add_argument("--iterations", type=int, default=8)
    args = parser.parse_args()
    train(Path(args.input), args.target, Path(args.output), args.iterations)
