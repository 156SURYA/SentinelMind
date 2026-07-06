# mlops/shadow_deployment.py
import numpy as np
import json
import os
from datetime import datetime
from sklearn.metrics import accuracy_score, f1_score

SHADOW_LOG_PATH = "data/processed/shadow_log.json"
EVAL_THRESHOLD = 0.05  # challenger must beat champion by this margin to be promoted


class ShadowDeployment:
    """
    Runs champion and challenger models side by side on live traffic.
    Logs challenger predictions without acting on them.
    Promotes challenger when it consistently outperforms champion.
    """

    def __init__(self, champion_model, challenger_model, model_name: str):
        self.champion = champion_model
        self.challenger = challenger_model
        self.model_name = model_name
        self.shadow_log = []

    def predict(self, X: np.ndarray) -> dict:
        """
        Champion prediction is returned and acted on.
        Challenger prediction is logged silently.
        """
        champion_pred = self.champion.predict(X)
        challenger_pred = self.challenger.predict(X)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "champion_prediction": int(champion_pred[0]),
            "challenger_prediction": int(challenger_pred[0]),
            "input_hash": hash(X.tobytes())
        }
        self.shadow_log.append(log_entry)
        self._save_log()

        return {
            "prediction": int(champion_pred[0]),
            "source": "champion"
        }

    def evaluate_challenger(self, X_eval: np.ndarray, y_true: np.ndarray) -> dict:
        """
        Compare champion vs challenger on analyst-confirmed ground truth.
        Call this periodically (e.g. daily) with labeled sessions.
        """
        champ_preds = self.champion.predict(X_eval)
        chall_preds = self.challenger.predict(X_eval)

        champ_f1 = f1_score(y_true, champ_preds, average="weighted")
        chall_f1 = f1_score(y_true, chall_preds, average="weighted")

        result = {
            "champion_f1": round(champ_f1, 4),
            "challenger_f1": round(chall_f1, 4),
            "delta": round(chall_f1 - champ_f1, 4),
            "promote_challenger": (chall_f1 - champ_f1) > EVAL_THRESHOLD
        }

        if result["promote_challenger"]:
            print(f"[Shadow] Challenger outperforms champion by {result['delta']:.4f}. Promoting.")
            self._promote_challenger()
        else:
            print(f"[Shadow] Champion holds. Delta: {result['delta']:.4f}")

        return result

    def _promote_challenger(self):
        from mlops.model_registry import promote_model
        promote_model(self.model_name, version=2, stage="Production")
        promote_model(self.model_name, version=1, stage="Archived")

    def _save_log(self):
        with open(SHADOW_LOG_PATH, "w") as f:
            json.dump(self.shadow_log[-500:], f, indent=2)  # keep last 500 entries