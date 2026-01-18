from pathlib import Path
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# --------------------------------------------------
# PROJECT ROOT
# anomaly_detector.py → AdaptiveSentinel/models/
# parents[2] → project root
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------- PATHS ----------------
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "behavior_features.csv"
MODEL_DIR = PROJECT_ROOT / "AdaptiveSentinel" / "models"
MODEL_PATH = MODEL_DIR / "anomaly_detector.pkl"

# 🔐 FEATURE CONTRACT
FEATURE_COLUMNS = [
    "pass_len",
    "user_len",
    "is_long_pass",
    "is_short_user",
    "requests_last_min",
    "unique_users_last_min",
]


# ---------------- TRAINING ----------------
def train_model():
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"❌ Features file not found: {FEATURES_PATH}"
        )

    df = pd.read_csv(FEATURES_PATH)

    missing = set(FEATURE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"❌ Missing required features for training: {missing}"
        )

    X = df[FEATURE_COLUMNS]

    model = IsolationForest(
        n_estimators=200,
        contamination=0.15,
        random_state=42,
    )

    model.fit(X)

    joblib.dump(
        {
            "model": model,
            "features": FEATURE_COLUMNS,
        },
        MODEL_PATH,
    )

    print(f"✅ Model trained on {len(X)} rows")
    print(f"📦 Model saved to {MODEL_PATH}")


# ---------------- LOADING ----------------
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"❌ Model not found at {MODEL_PATH}. Train it first."
        )

    payload = joblib.load(MODEL_PATH)

    # Backward compatibility
    if isinstance(payload, dict):
        return payload["model"], payload["features"]

    return payload, FEATURE_COLUMNS


# ---------------- REALTIME SCORING ----------------
def score_request(event: dict) -> float:
    model, features = load_model()

    row = {
        "pass_len": event.get("pass_len", 0),
        "user_len": len(event.get("user", "")),
        "is_long_pass": int(event.get("pass_len", 0) > 12),
        "is_short_user": int(len(event.get("user", "")) < 4),
        "requests_last_min": event.get("requests_last_min", 1),
        "unique_users_last_min": event.get("unique_users_last_min", 1),
    }

    df = pd.DataFrame([row])[features]

    score = model.decision_function(df)[0]
    return float(score)


# ---------------- CLI ENTRY ----------------
if __name__ == "__main__":
    train_model()
