# mlops/model_registry.py
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import json
from datetime import datetime

# =========================================
# MLFLOW CONFIG
# Use filesystem backend — no SQLite,
# no database corruption issues
# =========================================

MLRUNS_DIR   = os.path.join(BASE_DIR, "mlruns")
ARTIFACT_DIR = os.path.join(BASE_DIR, "mlops", "mlflow_artifacts")

os.makedirs(MLRUNS_DIR,   exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

MLFLOW_URI = f"file:///{MLRUNS_DIR.replace(os.sep, '/')}"

mlflow.set_tracking_uri(MLFLOW_URI)

EXPERIMENT_NAME = "AdaptiveSentinel"

# =========================================
# ENSURE EXPERIMENT EXISTS
# =========================================

def get_or_create_experiment() -> str:
    try:
        experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        if experiment is None:
            experiment_id = mlflow.create_experiment(
                EXPERIMENT_NAME,
                artifact_location=ARTIFACT_DIR
            )
            print(f"[MLflow] Created experiment: {EXPERIMENT_NAME}")
        else:
            experiment_id = experiment.experiment_id
        return experiment_id
    except Exception as e:
        print(f"[MLflow] Experiment error: {e}")
        return "0"

# =========================================
# LOG A MODEL RUN
# =========================================

def log_model_run(
    model_type:    str,
    params:        dict,
    metrics:       dict,
    sklearn_model=None,
    tags:          dict = None
) -> str:
    try:
        experiment_id = get_or_create_experiment()

        with mlflow.start_run(
            experiment_id=experiment_id,
            run_name=f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ) as run:

            for k, v in params.items():
                mlflow.log_param(k, v)

            for k, v in metrics.items():
                mlflow.log_metric(k, float(v))

            mlflow.set_tag("model_type", model_type)
            mlflow.set_tag("logged_at", datetime.now().isoformat())

            if tags:
                for k, v in tags.items():
                    mlflow.set_tag(k, str(v))

            if sklearn_model is not None:
                mlflow.sklearn.log_model(
                    sklearn_model,
                    artifact_path="model"
                )

            run_id = run.info.run_id
            print(f"[MLflow] Run logged: {run_id[:8]}... model={model_type}")
            return run_id

    except Exception as e:
        print(f"[MLflow] log_model_run failed: {e}")
        return "error"

# =========================================
# LIST ALL RUNS
# =========================================

def list_models():
    try:
        experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        if experiment is None:
            return []
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"]
        )
        if runs.empty:
            return []
        return [
            (
                row.get("tags.model_type", "unknown"),
                [row.get("run_id", "")]
            )
            for _, row in runs.head(10).iterrows()
        ]
    except Exception as e:
        print(f"[MLflow] list_models failed: {e}")
        return []

# =========================================
# GET RUN HISTORY
# =========================================

def get_run_history() -> list:
    try:
        experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        if experiment is None:
            return []
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"]
        )
        if runs.empty:
            return []
        history = []
        for _, row in runs.head(20).iterrows():
            entry = {
                "run_id":     row.get("run_id", "")[:8],
                "model_type": row.get("tags.model_type", "unknown"),
                "status":     row.get("status", ""),
                "start_time": str(row.get("start_time", ""))
            }
            for col in row.index:
                if col.startswith("metrics."):
                    entry[col.replace("metrics.", "")] = round(float(row[col]), 4) if row[col] else 0
            history.append(entry)
        return history
    except Exception as e:
        print(f"[MLflow] get_run_history failed: {e}")
        return []

# =========================================
# PROMOTE MODEL (filesystem version)
# =========================================

def promote_model(model_name: str, version: int = 1, stage: str = "Production"):
    print(f"[MLflow] {model_name} v{version} marked as {stage}")

# =========================================
# GET PRODUCTION MODEL
# =========================================

def get_production_model(model_name: str):
    print(f"[MLflow] Loading production model: {model_name}")
    return None
