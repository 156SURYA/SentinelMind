# mlops/conformal_predictor.py
import numpy as np
from mapie.classification import MapieClassifier
from sklearn.base import BaseEstimator
import joblib
import os

MODEL_PATH = "mlops/conformal_model.pkl"


class ConformalThreatPredictor:
    """
    Wraps any sklearn classifier with conformal prediction.
    Produces guaranteed coverage intervals instead of raw probabilities.
    """

    def __init__(self, base_classifier: BaseEstimator, coverage: float = 0.95):
        self.coverage = coverage
        self.mapie = MapieClassifier(
            estimator=base_classifier,
            method="raps",
            cv=5
        )
        self.label_map = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "CRITICAL"}

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.mapie.fit(X, y)
        joblib.dump(self.mapie, MODEL_PATH)
        print("[Conformal] Model fitted and saved.")

    def predict(self, X: np.ndarray):
        predictions, sets = self.mapie.predict(X, alpha=1 - self.coverage)

        results = []
        for pred, pred_set in zip(predictions, sets):
            severity = self.label_map.get(int(pred), "UNKNOWN")
            coverage_set = [self.label_map[i] for i, included in enumerate(pred_set) if included]
            results.append({
                "severity": severity,
                "confidence": round(float(self.coverage), 2),
                "prediction_set": coverage_set  # guaranteed to contain true label 95% of the time
            })
        return results

    @classmethod
    def load(cls):
        if os.path.exists(MODEL_PATH):
            instance = cls.__new__(cls)
            instance.mapie = joblib.load(MODEL_PATH)
            instance.label_map = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "CRITICAL"}
            instance.coverage = 0.95
            return instance
        raise FileNotFoundError("No conformal model found. Run fit() first.")