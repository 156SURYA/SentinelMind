import pandas as pd
from pathlib import Path

from AdaptiveSentinel.monitoring.drift_detection import check_drift
from AdaptiveSentinel.models.score_anomalies import score_recent_events
from AdaptiveSentinel.monitoring.alert import get_active_alerts


# ---------------- CONFIG ----------------
ANOMALY_LIMIT = -0.1
ALERT_THRESHOLD = 5


def get_system_health():
    """
    Global health status for AdaptiveSentinel.
    This is the brain of the system.
    """

    # 1️⃣ Drift
    drift = check_drift()
    drift_score = drift["drift_score"]
    drift_status = drift["status"]

    if drift_score < 0.2:
        drift_level = "LOW"
    elif drift_score < 0.5:
        drift_level = "MODERATE"
    else:
        drift_level = "HIGH"

    # 2️⃣ Anomaly behavior
    recent_scores = score_recent_events(limit=200)

    if recent_scores:
        avg_anomaly = round(sum(recent_scores) / len(recent_scores), 4)
    else:
        avg_anomaly = 0.0

    anomaly_status = "UNSTABLE" if avg_anomaly < ANOMALY_LIMIT else "STABLE"

    # 3️⃣ Alerts
    alerts = get_active_alerts()
    alert_count = len(alerts)

    # 4️⃣ FINAL DECISION
    if drift_level == "HIGH" or alert_count >= ALERT_THRESHOLD:
        system_decision = "RETRAIN"
    elif drift_level == "MODERATE" or anomaly_status == "UNSTABLE":
        system_decision = "MONITOR"
    else:
        system_decision = "STABLE"

    return {
        "drift_level": drift_level,
        "drift_score": drift_score,
        "avg_anomaly_score": avg_anomaly,
        "alerts_active": alert_count,
        "system_decision": system_decision,
    }


# ---------------- CLI DEBUG ----------------
if __name__ == "__main__":
    from pprint import pprint
    pprint(get_system_health())
