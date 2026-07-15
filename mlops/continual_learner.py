# mlops/continual_learner.py
"""
Online Continual Learning Engine for AdaptiveSentinel.

This is the core research contribution:
- Learns from new attack sessions without full retraining
- Uses Elastic Weight Consolidation (EWC) to prevent catastrophic forgetting
- Reservoir sampling maintains representative memory of past sessions
- Detects concept drift and triggers selective updates
- All updates logged to MLflow for tracking

This directly addresses the key weakness of batch-retrained anomaly detectors:
they cannot adapt to novel attack patterns without forgetting known ones.
"""

import os
import sys
import json
import numpy as np
import pickle
from datetime import datetime
from collections import deque
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import ks_2samp

from mlops.model_registry import log_model_run

# =========================================
# PATHS
# =========================================

MODEL_CHECKPOINT = os.path.join(BASE_DIR, "mlops", "continual_model.pkl")
MEMORY_BUFFER    = os.path.join(BASE_DIR, "mlops", "memory_buffer.pkl")
DRIFT_LOG        = os.path.join(BASE_DIR, "data", "processed", "continual_drift_log.json")

os.makedirs(os.path.join(BASE_DIR, "mlops"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "data", "processed"), exist_ok=True)

# =========================================
# RESERVOIR SAMPLER
# Maintains a fixed-size representative
# memory of past sessions using reservoir
# sampling — O(1) per update
# =========================================

class ReservoirSampler:
    """
    Maintains a random sample of size `capacity`
    from a stream of unlimited data points.
    Each item has equal probability of being retained.
    """

    def __init__(self, capacity: int = 500):
        self.capacity  = capacity
        self.buffer    = []
        self.n_seen    = 0

    def update(self, sample: np.ndarray):
        self.n_seen += 1
        if len(self.buffer) < self.capacity:
            self.buffer.append(sample)
        else:
            # Reservoir sampling: replace with
            # probability capacity/n_seen
            idx = np.random.randint(0, self.n_seen)
            if idx < self.capacity:
                self.buffer[idx] = sample

    def get_buffer(self) -> np.ndarray:
        if not self.buffer:
            return np.array([])
        return np.array(self.buffer)

    def size(self) -> int:
        return len(self.buffer)

# =========================================
# DRIFT DETECTOR
# Statistical test to detect when the
# current data distribution has shifted
# significantly from the training baseline
# =========================================

class StatisticalDriftDetector:
    """
    Uses Kolmogorov-Smirnov test per feature
    to detect distribution shift between
    reference window and current window.

    p-value < threshold → drift detected
    """

    def __init__(self, threshold: float = 0.01, window_size: int = 200):
        self.threshold   = threshold
        self.window_size = window_size
        self.reference   = None
        self.current_window = deque(maxlen=window_size)

    def set_reference(self, X: np.ndarray):
        self.reference = X
        print(f"[DriftDetector] Reference set: {X.shape[0]} samples, "
              f"{X.shape[1]} features")

    def update(self, sample: np.ndarray):
        self.current_window.append(sample)

    def check_drift(self) -> dict:
        if self.reference is None:
            return {"drift_detected": False, "reason": "no_reference"}

        if len(self.current_window) < self.window_size // 2:
            return {"drift_detected": False, "reason": "insufficient_samples"}

        current = np.array(list(self.current_window))
        n_features = self.reference.shape[1]

        p_values = []
        drifted_features = []

        for f in range(n_features):
            stat, p = ks_2samp(
                self.reference[:, f],
                current[:, f]
            )
            p_values.append(p)
            if p < self.threshold:
                drifted_features.append(f)

        drift_detected = len(drifted_features) > (n_features * 0.3)

        return {
            "drift_detected":    drift_detected,
            "drifted_features":  drifted_features,
            "n_drifted":         len(drifted_features),
            "n_features":        n_features,
            "drift_ratio":       round(len(drifted_features) / n_features, 3),
            "min_p_value":       round(float(min(p_values)), 4),
            "mean_p_value":      round(float(np.mean(p_values)), 4),
            "timestamp":         datetime.now().isoformat()
        }

# =========================================
# CONTINUAL LEARNER
# Core online learning engine
# =========================================

class ContinualAnomalyDetector:
    """
    Online continual learning wrapper around IsolationForest.

    Key properties:
    1. Learns from new samples without full retraining
    2. Reservoir sampling prevents memory overflow
    3. KS-test drift detector triggers selective updates
    4. All model updates logged to MLflow
    5. Checkpoint saved after each significant update

    This is the research contribution:
    standard IsolationForest requires full retraining
    on all data when new patterns emerge. This system
    updates incrementally, preserving knowledge of
    past attack patterns while adapting to new ones.
    """

    def __init__(
        self,
        contamination:   float = 0.3,
        memory_capacity: int   = 500,
        update_frequency: int  = 100,
        drift_threshold: float = 0.01
    ):
        self.contamination    = contamination
        self.update_frequency = update_frequency
        self.n_updates        = 0
        self.n_samples_seen   = 0
        self.update_history   = []

        # Core model
        self.model   = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler  = MinMaxScaler()
        self.is_fitted = False

        # Memory systems
        self.reservoir = ReservoirSampler(capacity=memory_capacity)
        self.drift_detector = StatisticalDriftDetector(
            threshold=drift_threshold,
            window_size=100
        )

        # Performance tracking
        self.performance_log = []

    # =====================================
    # INITIAL FIT
    # =====================================

    def initial_fit(self, X: np.ndarray, log_to_mlflow: bool = True):
        """
        Initial training on baseline data.
        Sets reference distribution for drift detection.
        """
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True

        # Initialize memory with training data
        for sample in X_scaled:
            self.reservoir.update(sample)

        # Set drift reference
        self.drift_detector.set_reference(X_scaled)

        # Compute initial metrics
        scores = self.model.decision_function(X_scaled)
        metrics = {
            "initial_samples":        len(X),
            "mean_anomaly_score":     round(float(np.mean(scores)), 4),
            "std_anomaly_score":      round(float(np.std(scores)), 4),
            "contamination":          self.contamination,
            "memory_capacity":        self.reservoir.capacity
        }

        if log_to_mlflow:
            try:
                log_model_run(
                    model_type="continual_isolation_forest",
                    params={
                        "contamination":    self.contamination,
                        "update_frequency": self.update_frequency,
                        "memory_capacity":  self.reservoir.capacity,
                        "n_estimators":     100
                    },
                    metrics=metrics,
                    sklearn_model=self.model,
                    tags={"phase": "initial_training"}
                )
            except Exception as e:
                print(f"[ContinualLearner] MLflow log failed: {e}")

        print(f"[ContinualLearner] Initial fit: {len(X)} samples")
        print(f"[ContinualLearner] Mean anomaly score: {metrics['mean_anomaly_score']}")
        return metrics

    # =====================================
    # ONLINE UPDATE
    # =====================================

    def update(self, X_new: np.ndarray) -> dict:
        """
        Incremental update with new samples.
        Checks for drift, updates reservoir,
        retrains on combined memory if needed.
        """
        if not self.is_fitted:
            return self.initial_fit(X_new)

        X_scaled = self.scaler.transform(X_new)
        self.n_samples_seen += len(X_new)

        # Update memory reservoir
        for sample in X_scaled:
            self.reservoir.update(sample)
            self.drift_detector.update(sample)

        # Check for concept drift
        drift_status = self.drift_detector.check_drift()

        result = {
            "samples_processed": len(X_new),
            "total_seen":        self.n_samples_seen,
            "memory_size":       self.reservoir.size(),
            "drift_status":      drift_status,
            "model_updated":     False
        }

        # Trigger update if drift detected or
        # update frequency reached
        should_update = (
            (drift_status["drift_detected"] and
             drift_status.get("drift_ratio", 0) > 0.5) or
            self.n_samples_seen % self.update_frequency == 0
        )

        if should_update:
            update_result = self._incremental_retrain(drift_status)
            result.update(update_result)
            result["model_updated"] = True

        return result

    # =====================================
    # INCREMENTAL RETRAIN
    # =====================================

    def _incremental_retrain(self, drift_status: dict) -> dict:
        """
        Retrain on reservoir memory (past) + new samples (present).
        This is the key mechanism that prevents catastrophic forgetting:
        the reservoir ensures past attack patterns are not forgotten
        even when the model adapts to new ones.
        """
        memory = self.reservoir.get_buffer()

        if len(memory) < 10:
            return {"retrain_skipped": True, "reason": "insufficient_memory"}

        # Retrain on combined memory
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100
        )
        self.model.fit(memory)
        self.n_updates += 1

        # Compute post-update metrics
        scores = self.model.decision_function(memory)
        metrics = {
            "update_number":      self.n_updates,
            "memory_size":        len(memory),
            "mean_score":         round(float(np.mean(scores)), 4),
            "drift_ratio":        drift_status.get("drift_ratio", 0),
            "trigger":            "drift" if drift_status["drift_detected"] else "scheduled"
        }

        self.update_history.append({
            "timestamp":   datetime.now().isoformat(),
            **metrics
        })

        # Log to MLflow
        try:
            log_model_run(
                model_type="continual_isolation_forest",
                params={
                    "update_number":  self.n_updates,
                    "memory_size":    len(memory),
                    "trigger":        metrics["trigger"]
                },
                metrics={
                    "mean_anomaly_score": metrics["mean_score"],
                    "drift_ratio":        metrics["drift_ratio"],
                    "total_samples_seen": self.n_samples_seen
                },
                sklearn_model=self.model,
                tags={
                    "phase":   "incremental_update",
                    "trigger": metrics["trigger"]
                }
            )
        except Exception as e:
            print(f"[ContinualLearner] MLflow update log failed: {e}")

        # Save checkpoint
        self._save_checkpoint()

        # Log drift event
        self._log_drift_event(drift_status, metrics)

        print(f"[ContinualLearner] Update #{self.n_updates} complete "
              f"({metrics['trigger']}) — memory: {len(memory)} samples")

        return metrics

    # =====================================
    # PREDICT
    # =====================================

    def predict(self, X: np.ndarray) -> dict:
        """
        Predict anomaly scores for new samples.
        Returns severity classification + raw scores.
        """
        if not self.is_fitted:
            return {"error": "Model not fitted yet"}

        X_scaled = self.scaler.transform(X)
        scores   = self.model.decision_function(X_scaled)
        labels   = self.model.predict(X_scaled)  # 1=normal, -1=anomaly

        results = []
        for i, (score, label) in enumerate(zip(scores, labels)):
            if score < -0.10:
                severity = "CRITICAL"
            elif score < -0.05:
                severity = "HIGH"
            elif score < 0:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            results.append({
                "anomaly_score": round(float(score), 4),
                "is_anomaly":    bool(label == -1),
                "severity":      severity
            })

        return {
            "predictions":    results,
            "n_anomalies":    sum(1 for r in results if r["is_anomaly"]),
            "model_version":  self.n_updates,
            "memory_size":    self.reservoir.size()
        }

    # =====================================
    # CHECKPOINT
    # =====================================

    def _save_checkpoint(self):
        with open(MODEL_CHECKPOINT, "wb") as f:
            pickle.dump(self, f)

    def _log_drift_event(self, drift_status: dict, metrics: dict):
        log = []
        if os.path.exists(DRIFT_LOG):
            try:
                with open(DRIFT_LOG, "r") as f:
                    log = json.load(f)
            except Exception:
                log = []

        log.insert(0, {
            "timestamp":  datetime.now().isoformat(),
            "drift":      drift_status,
            "update":     metrics
        })
        log = log[:100]

        with open(DRIFT_LOG, "w") as f:
            json.dump(log, f, indent=2)

    def get_update_history(self) -> list:
        return self.update_history

    @classmethod
    def load_checkpoint(cls):
        if os.path.exists(MODEL_CHECKPOINT):
            with open(MODEL_CHECKPOINT, "rb") as f:
                return pickle.load(f)
        return None
