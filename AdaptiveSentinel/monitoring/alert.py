import pandas as pd
from pathlib import Path
from datetime import datetime

# ---------------- PATH ----------------
SCORED_PATH = Path("data/processed/scored_logs.csv")


def alert_if_anomaly(df=None):
    """
    Checks latest event and triggers alert if anomalous.
    """

    if df is None:
        if not SCORED_PATH.exists():
            return
        df = pd.read_csv(SCORED_PATH)

    if df.empty:
        return

    latest = df.iloc[-1]

    if latest.get("status") == "anomaly":
        print("\n🚨 ALERT: Anomalous login detected!")
        print(latest)


def get_active_alerts(window=20):
    """
    Sentinel-compatible alert query.
    Returns recent anomalous events.
    """

    if not SCORED_PATH.exists():
        return []

    df = pd.read_csv(SCORED_PATH)

    if df.empty or "status" not in df.columns:
        return []

    recent = df.tail(window)
    alerts = recent[recent["status"] == "anomaly"]

    records = []
    for _, row in alerts.iterrows():
        records.append({
            "timestamp": row.get("timestamp", str(datetime.utcnow())),
            "score": row.get("anomaly_score"),
            "type": "anomaly"
        })

    return records


# ---------------- CLI DEBUG ----------------
if __name__ == "__main__":
    alert_if_anomaly()
