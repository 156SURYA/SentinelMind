# mlops/drift_monitor.py
import pandas as pd
import numpy as np
import json
import os
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently.metrics import DatasetDriftMetric
from datetime import datetime

BASELINE_PATH = "data/processed/baseline_embeddings.csv"
DRIFT_REPORT_PATH = "data/processed/drift_reports/"
DRIFT_THRESHOLD = 0.15  # Jensen-Shannon divergence threshold

os.makedirs(DRIFT_REPORT_PATH, exist_ok=True)


def save_baseline(embeddings: np.ndarray):
    """
    Call this once after initial training to save the reference distribution.
    embeddings: shape (n_sessions, embedding_dim)
    """
    df = pd.DataFrame(embeddings, columns=[f"dim_{i}" for i in range(embeddings.shape[1])])
    df.to_csv(BASELINE_PATH, index=False)
    print(f"[Drift] Baseline saved: {embeddings.shape[0]} sessions.")


def check_drift(current_embeddings: np.ndarray) -> dict:
    """
    Compare current session embeddings against the saved baseline.
    Returns drift status and triggers alert if threshold exceeded.
    """
    if not os.path.exists(BASELINE_PATH):
        print("[Drift] No baseline found. Skipping drift check.")
        return {"drift_detected": False, "reason": "no_baseline"}

    baseline_df = pd.read_csv(BASELINE_PATH)
    current_df = pd.DataFrame(
        current_embeddings,
        columns=[f"dim_{i}" for i in range(current_embeddings.shape[1])]
    )

    report = Report(metrics=[
        DataDriftPreset(),
        DatasetDriftMetric()
    ])
    report.run(reference_data=baseline_df, current_data=current_df)

    result = report.as_dict()
    drift_detected = result["metrics"][1]["result"]["dataset_drift"]
    share_drifted = result["metrics"][1]["result"]["share_of_drifted_columns"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"{DRIFT_REPORT_PATH}drift_{timestamp}.html"
    report.save_html(report_path)

    status = {
        "drift_detected": drift_detected,
        "share_drifted_features": round(share_drifted, 3),
        "report_path": report_path,
        "timestamp": timestamp
    }

    if drift_detected and share_drifted > DRIFT_THRESHOLD:
        _trigger_alert(status)

    return status


def _trigger_alert(status: dict):
    """
    Write alert to a JSON file. Wire this to Slack/email/PagerDuty in production.
    """
    alert_path = "data/processed/drift_alert.json"
    with open(alert_path, "w") as f:
        json.dump(status, f, indent=2)
    print(f"[Drift] ALERT: Significant drift detected. Report at {status['report_path']}")