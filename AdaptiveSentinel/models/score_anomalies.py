import pandas as pd
from pathlib import Path

from AdaptiveSentinel.models.anomaly_detector import load_model
from AdaptiveSentinel.monitoring.alert import alert_if_anomaly

from AdaptiveSentinel.sentinel.threat import compute_threat_score, threat_level
from AdaptiveSentinel.sentinel.decision import decide_action


# ---------------- PATHS ----------------
FEATURES_PATH = Path("data/processed/behavior_features.csv")
OUT_PATH = Path("data/processed/scored_logs.csv")

# ---------------- CONFIG ----------------
ANOMALY_THRESHOLD = -0.05

# 🔐 FEATURE CONTRACT (MUST MATCH TRAINING)
EXPECTED_FEATURES = [
    "pass_len",
    "user_len",
    "is_long_pass",
    "is_short_user",
    "requests_last_min",
    "unique_users_last_min",
]


# ---------------- FEATURE SAFETY ----------------
def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    missing = set(EXPECTED_FEATURES) - set(df.columns)
    if missing:
        raise ValueError(f"❌ Missing required features: {missing}")

    return df[EXPECTED_FEATURES]


# ---------------- SCORING (FOR SENTINEL / HEALTH) ----------------
def score_recent_events(limit=200):
    if not FEATURES_PATH.exists():
        return []

    df = pd.read_csv(FEATURES_PATH)

    if df.empty:
        return []

    if len(df) > limit:
        df = df.tail(limit)

    df_model = _prepare_features(df)

    model, _ = load_model()   # ✅ UNPACK
    scores = model.decision_function(df_model)

    return scores.tolist()


# ---------------- MAIN PIPELINE ----------------
def score_and_persist():
    if not FEATURES_PATH.exists():
        print("⚠ No features file found.")
        return

    df = pd.read_csv(FEATURES_PATH)

    if df.empty:
        print("⚠ No data to score.")
        return

    df_model = _prepare_features(df)

    model, _ = load_model()   # ✅ UNPACK
    scores = model.decision_function(df_model)

    # ---------- Anomaly ----------
    df["anomaly_score"] = scores
    df["status"] = df["anomaly_score"].apply(
        lambda x: "anomaly" if x < ANOMALY_THRESHOLD else "normal"
    )

    # ---------- Threat & Decision ----------
    df["threat_score"] = df.apply(compute_threat_score, axis=1)
    df["threat_level"] = df["threat_score"].apply(threat_level)
    df["decision"] = df["threat_level"].apply(decide_action)

    # ---------- Save ----------
    df.to_csv(OUT_PATH, index=False)
    print(f"✅ Scored {len(df)} rows -> {OUT_PATH}")

    # ---------- Alert ----------
    alert_if_anomaly(df)




# ---------------- API ENTRY (FastAPI uses this) ----------------
def score_events(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score incoming events (used by FastAPI /predict endpoint)
    """
    df_model = _prepare_features(df)

    model, _ = load_model()   # ✅ UNPACK
    scores = model.decision_function(df_model)

    # ---------- Anomaly ----------
    df["anomaly_score"] = scores
    df["status"] = df["anomaly_score"].apply(
        lambda x: "anomaly" if x < ANOMALY_THRESHOLD else "normal"
    )

    # ---------- Threat & Decision ----------
    df["threat_score"] = df.apply(compute_threat_score, axis=1)
    df["threat_level"] = df["threat_score"].apply(threat_level)
    df["decision"] = df["threat_level"].apply(decide_action)

    # ---------- Alert ----------
    alert_if_anomaly(df)

    return df


# ---------------- CLI ENTRY ----------------
if __name__ == "__main__":
    score_and_persist()
