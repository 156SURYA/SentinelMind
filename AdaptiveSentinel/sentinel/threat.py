import pandas as pd

# ---------------- CONFIG ----------------
THREAT_WEIGHTS = {
    "anomaly": 0.5,
    "rate": 0.2,
    "spread": 0.15,
    "password": 0.1,
    "username": 0.05,
}


def compute_threat_score(row: pd.Series) -> float:
    """
    Combines ML anomaly score + behavioral signals
    into a normalized threat score (0 → 1)
    """

    # 1️⃣ Anomaly score (IsolationForest: lower = more anomalous)
    anomaly_component = min(abs(row["anomaly_score"]) * 2, 1.0)

    # 2️⃣ Request rate (brute force)
    rate_component = min(row["requests_last_min"] / 100, 1.0)

    # 3️⃣ User spread (scanning)
    spread_component = min(row["unique_users_last_min"] / 20, 1.0)

    # 4️⃣ Password pattern
    password_component = 1.0 if row["is_long_pass"] else 0.0

    # 5️⃣ Username pattern
    username_component = 1.0 if row["is_short_user"] else 0.0

    threat_score = (
        anomaly_component * THREAT_WEIGHTS["anomaly"]
        + rate_component * THREAT_WEIGHTS["rate"]
        + spread_component * THREAT_WEIGHTS["spread"]
        + password_component * THREAT_WEIGHTS["password"]
        + username_component * THREAT_WEIGHTS["username"]
    )

    return round(min(threat_score, 1.0), 3)


def threat_level(threat_score: float) -> str:
    if threat_score < 0.3:
        return "LOW"
    elif threat_score < 0.6:
        return "MEDIUM"
    return "HIGH"
