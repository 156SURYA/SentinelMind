from sklearn.ensemble import IsolationForest
from sklearn.datasets import make_blobs
from mlops.model_registry import log_model_run


# Create dummy dataset
X, _ = make_blobs(
    n_samples=100,
    centers=3,
    n_features=2,
    random_state=42
)

# Train model
model = IsolationForest(
    contamination=0.1,
    random_state=42
)

model.fit(X)

# Log + register into MLflow
run_id = log_model_run(
    model_type="anomaly_engine",
    params={
        "contamination": 0.1
    },
    metrics={
        "f1": 0.95
    },
    sklearn_model=model
)

print("Run ID:", run_id)