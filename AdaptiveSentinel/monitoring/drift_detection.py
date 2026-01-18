import pandas as pd
from pathlib import Path
from scipy.stats import ks_2samp

# ---------------- PATHS ----------------
FEATURES_PATH = Path("data/processed/behavior_features.csv")

# 🔐 FEATURES THAT DRIVE THE MODEL
DRIFT_FEATURES = [
    "pass_len",
    "user_len",
    "requests_last_min",
    "unique_users_last_min",
]

# ---------------- CONFIG ----------------
WINDOW = 50
P_THRESHOLD = 0.05


def _detect_drift_for_column(df, col):
    """
    Runs KS test for a single feature.
    Compares historical vs recent window.
    """
    ref = df[col].iloc[:-WINDOW]
    cur = df[col].iloc[-WINDOW:]

    stat, p = ks_2samp(ref, cur)

    return {
        "ks_stat": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "drift": p < P_THRESHOLD,
    }


def check_drift():
    """
    Sentinel-compatible drift checker.
    Returns structured drift summary.
    """

    if not FEATURES_PATH.exists():
        return {
            "drift_score": 0.0,
            "drifted_features": [],
            "details": {},
            "status": "NO_DATA",
        }

    df = pd.read_csv(FEATURES_PATH)

    if len(df) < 2 * WINDOW:
        return {
            "drift_score": 0.0,
            "drifted_features": [],
            "details": {},
            "status": "INSUFFICIENT_DATA",
        }

    results = {}
    drifted = []

    for col in DRIFT_FEATURES:
        if col not in df.columns:
            continue

        res = _detect_drift_for_column(df, col)
        results[col] = res

        if res["drift"]:
            drifted.append(col)

    drift_score = len(drifted) / len(DRIFT_FEATURES)

    return {
        "drift_score": round(drift_score, 3),
        "drifted_features": drifted,
        "details": results,
        "status": "DRIFT" if drift_score >= 0.3 else "OK",
    }


# ---------------- CLI DEBUG ----------------
if __name__ == "__main__":
    summary = check_drift()

    print("\n📊 Drift Summary")
    print("----------------")
    print(f"Status        : {summary['status']}")
    print(f"Drift score   : {summary['drift_score']}")
    print(f"Drifted feats : {summary['drifted_features']}")

    for feat, info in summary["details"].items():
        print(
            f"{feat}: KS={info['ks_stat']}, "
            f"p={info['p_value']}, "
            f"drift={info['drift']}"
        )
