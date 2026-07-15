# mlops/benchmark.py
"""
Benchmark: Batch IsolationForest vs Continual Online Learner
Runs standalone — no MLflow, no external dependencies beyond sklearn/numpy
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, accuracy_score
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from scipy.stats import ks_2samp
from collections import deque

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

RESULTS_DIR = os.path.join(BASE_DIR, "research", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# =========================================
# INLINE RESERVOIR SAMPLER
# =========================================

class ReservoirSampler:
    def __init__(self, capacity=300):
        self.capacity = capacity
        self.buffer   = []
        self.n_seen   = 0

    def update(self, sample):
        self.n_seen += 1
        if len(self.buffer) < self.capacity:
            self.buffer.append(sample)
        else:
            idx = np.random.randint(0, self.n_seen)
            if idx < self.capacity:
                self.buffer[idx] = sample

    def get(self):
        return np.array(self.buffer) if self.buffer else np.array([])

# =========================================
# INLINE DRIFT DETECTOR
# =========================================

class DriftDetector:
    def __init__(self, threshold=0.001, window_size=150):
        self.threshold   = threshold
        self.window_size = window_size
        self.reference   = None
        self.window      = deque(maxlen=window_size)

    def set_reference(self, X):
        self.reference = X

    def update(self, sample):
        self.window.append(sample)

    def check(self):
        if self.reference is None or len(self.window) < self.window_size:
            return False, 0.0
        current  = np.array(list(self.window))
        n_feat   = self.reference.shape[1]
        drifted  = 0
        for f in range(n_feat):
            _, p = ks_2samp(self.reference[:, f], current[:, f])
            if p < self.threshold:
                drifted += 1
        ratio = drifted / n_feat
        return ratio > 0.4, ratio   # 40% features must drift

# =========================================
# INLINE CONTINUAL DETECTOR
# =========================================

class ContinualDetector:
    def __init__(self, contamination=0.3, capacity=300, update_freq=75):
        self.contamination = contamination
        self.update_freq   = update_freq
        self.n_seen        = 0
        self.n_updates     = 0
        self.model         = IsolationForest(contamination=contamination, random_state=42)
        self.scaler        = MinMaxScaler()
        self.fitted        = False
        self.reservoir     = ReservoirSampler(capacity)
        self.drift         = DriftDetector(threshold=0.005, window_size=100)

    def initial_fit(self, X):
        Xs = self.scaler.fit_transform(X)
        self.model.fit(Xs)
        self.fitted = True
        for s in Xs:
            self.reservoir.update(s)
        self.drift.set_reference(Xs)
        print(f"  [Continual] Initial fit: {len(X)} samples")

    def update(self, X_new):
        if not self.fitted:
            return
        Xs = self.scaler.transform(X_new)
        self.n_seen += len(Xs)
        for s in Xs:
            self.reservoir.update(s)
            self.drift.update(s)

        drift_detected, ratio = self.drift.check()
        should_update = (
            (drift_detected and ratio > 0.4) or
            (self.n_seen % self.update_freq == 0)
        )
        if should_update:
            mem = self.reservoir.get()
            if len(mem) >= 10:
                self.model = IsolationForest(
                    contamination=self.contamination,
                    random_state=42
                )
                self.model.fit(mem)
                self.n_updates += 1
                trigger = "drift" if drift_detected else "scheduled"
                print(f"  [Continual] Update #{self.n_updates} ({trigger}) "
                      f"— memory: {len(mem)}, seen: {self.n_seen}")

    def score(self, X):
        Xs = self.scaler.transform(X)
        return self.model.decision_function(Xs)

# =========================================
# DATA GENERATION
# =========================================

def make_stream(n_normal=500, n_attack=150, n_features=10,
                drift_magnitude=4.0, seed=42):  # stronger drift
    np.random.seed(seed)
    X_normal     = np.random.randn(n_normal, n_features) * 0.5
    X_attack_pre = np.random.randn(n_attack // 2, n_features) * 0.8 + 2.0
    X_attack_post= np.random.randn(n_attack - n_attack//2, n_features) * 0.8 + drift_magnitude
    y_normal     = np.zeros(n_normal)
    y_pre        = np.ones(n_attack // 2)
    y_post       = np.ones(n_attack - n_attack // 2)
    X = np.vstack([X_normal, X_attack_pre, X_attack_post])
    y = np.concatenate([y_normal, y_pre, y_post])
    idx = np.random.permutation(len(X))
    return X[idx], y[idx]

# =========================================
# METRICS
# =========================================

def metrics(y_true, scores, threshold=0.0):
    y_pred = (scores < threshold).astype(int)
    try:
        auc = roc_auc_score(y_true, -scores)
    except Exception:
        auc = 0.0
    return {
        "f1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
        "accuracy":  round(accuracy_score(y_true, y_pred), 4),
        "auc_roc":   round(auc, 4)
    }

# =========================================
# BATCH BASELINE
# =========================================

def run_batch(X, y):
    X_train, X_test, _, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )
    sc = MinMaxScaler()
    X_tr = sc.fit_transform(X_train)
    X_te = sc.transform(X_test)
    m = IsolationForest(contamination=0.3, random_state=42)
    m.fit(X_tr)
    scores = m.decision_function(X_te)
    return metrics(y_test, scores)

# =========================================
# CONTINUAL BASELINE
# =========================================

def run_continual(X, y):
    det = ContinualDetector(
        contamination=0.3,
        capacity=300,
        update_freq=75
    )
    init_n = len(X) // 5
    det.initial_fit(X[:init_n])

    all_scores, all_labels = [], []
    for i in range(init_n, len(X)):
        s    = det.score(X[i:i+1])
        all_scores.append(s[0])
        all_labels.append(y[i])
        det.update(X[i:i+1])

    return metrics(np.array(all_labels), np.array(all_scores))

# =========================================
# MAIN BENCHMARK
# =========================================

def run_benchmark(n_runs=5):
    print("\n" + "="*60)
    print("ADAPTIVESENTINEL — BENCHMARK EVALUATION")
    print("Batch IsolationForest vs Continual Online Learner")
    print("="*60)

    batch_results     = []
    continual_results = []

    for seed in range(n_runs):
        print(f"\n[Run {seed+1}/{n_runs}] seed={seed}")
        X, y = make_stream(
            n_normal=500, n_attack=150,
            n_features=10, drift_magnitude=4.0,
            seed=seed
        )

        print(f"  Dataset: {len(X)} samples, "
              f"{int(y.sum())} attacks ({y.mean()*100:.1f}%)")

        b = run_batch(X, y)
        batch_results.append(b)
        print(f"  Batch     → F1:{b['f1']:.4f}  "
              f"Prec:{b['precision']:.4f}  "
              f"Rec:{b['recall']:.4f}  "
              f"AUC:{b['auc_roc']:.4f}")

        c = run_continual(X, y)
        continual_results.append(c)
        print(f"  Continual → F1:{c['f1']:.4f}  "
              f"Prec:{c['precision']:.4f}  "
              f"Rec:{c['recall']:.4f}  "
              f"AUC:{c['auc_roc']:.4f}")

    # Aggregate
    def agg(results):
        keys = results[0].keys()
        return {
            k: {
                "mean": round(float(np.mean([r[k] for r in results])), 4),
                "std":  round(float(np.std([r[k] for r in results])),  4)
            }
            for k in keys
        }

    summary = {
        "batch_baseline":    agg(batch_results),
        "continual_learner": agg(continual_results),
        "n_runs": n_runs,
        "timestamp": datetime.now().isoformat()
    }

    # Print final table
    print("\n" + "="*65)
    print("FINAL RESULTS TABLE")
    print("="*65)
    print(f"{'Metric':<12} {'Batch mean±std':<22} {'Continual mean±std':<22} {'Delta'}")
    print("-"*65)

    for metric in ["f1", "precision", "recall", "accuracy", "auc_roc"]:
        b = summary["batch_baseline"][metric]
        c = summary["continual_learner"][metric]
        delta = round(c["mean"] - b["mean"], 4)
        sign  = "+" if delta >= 0 else ""
        print(
            f"{metric:<12} "
            f"{b['mean']:.4f} ± {b['std']:.4f}      "
            f"{c['mean']:.4f} ± {c['std']:.4f}      "
            f"{sign}{delta}"
        )

    print("="*65)

    improvement = summary["continual_learner"]["f1"]["mean"] - \
                  summary["batch_baseline"]["f1"]["mean"]

    if improvement > 0:
        print(f"\n✅ Continual learner outperforms batch by "
              f"+{improvement:.4f} F1 under concept drift")
    else:
        print(f"\n⚠️  Batch baseline holds — "
              f"delta F1: {improvement:.4f}")

    print(f"\nKey finding: Continual learner made "
          f"{sum(r.get('n_updates',0) for r in continual_results)} "
          f"incremental updates across {n_runs} runs")

    # Save results
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"benchmark_{ts}.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[Benchmark] Results saved → {path}")

    return summary


if __name__ == "__main__":
    run_benchmark(n_runs=5)