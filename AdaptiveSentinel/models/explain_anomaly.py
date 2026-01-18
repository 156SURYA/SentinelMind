import pandas as pd
import joblib
from pathlib import Path

# Find project root
BASE_DIR = Path(__file__).resolve().parents[1]

# Paths
MODEL_PATH = BASE_DIR / "models" / "anomaly_detector.pkl"
DATA_PATH = BASE_DIR / "data" / "processed" / "behavior_features.csv"

FEATURE_COLS = [
    "user_len",
    "pass_len",
    "is_short_user",
    "is_long_pass",
]

def explain_latest(n=3):
    # Load data
    df = pd.read_csv(DATA_PATH)

    # Load model
    model = joblib.load(MODEL_PATH)

    # Feature matrix
    X = df[FEATURE_COLS]

    # Get anomaly scores
    scores = model.decision_function(X)
    df["anomaly_score"] = scores

    # Take most anomalous rows
    anomalies = df.sort_values("anomaly_score").head(n)

    # Baseline = average behavior
    baseline = X.mean()

    print("\n🔍 Explaining recent anomalies:\n")

    for _, row in anomalies.iterrows():
        diffs = (row[FEATURE_COLS] - baseline).abs()
        reasons = diffs.sort_values(ascending=False).head(2)

        print("User:", row.get("user", "unknown"))
        print("Anomaly score:", row["anomaly_score"])
        print("Top reasons:")
        for k, v in reasons.items():
            print(f"  - {k}: deviation {round(v, 3)}")
        print("-" * 30)


if __name__ == "__main__":
    explain_latest()
