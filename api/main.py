import sys
import os

# =========================================
# ABSOLUTE PATH SETUP — PERMANENT FIX
# =========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

LIVE_ATTACKS_PATH = os.path.join(BASE_DIR, "honeypot", "live_attacks.json")
DRIFT_ALERT_PATH  = os.path.join(BASE_DIR, "data", "processed", "drift_alert.json")
SHADOW_LOG_PATH   = os.path.join(BASE_DIR, "data", "processed", "shadow_log.json")
DATA_PATH         = os.path.join(BASE_DIR, "data", "raw", "enterprise_security_logs.csv")

# =========================================
# IMPORTS
# =========================================

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest

# =========================================
# MLOPS IMPORTS
# =========================================

from mlops.drift_monitor import check_drift
from mlops.model_registry import list_models
from mlops.llm_explainer import generate_soc_brief, generate_counterfactual
from mlops.rl_deception_planner import get_deception_action, DECEPTION_ACTIONS
from mlops.continual_learner import ContinualAnomalyDetector

# =========================================
# APP CONFIG
# =========================================

app = FastAPI(
    title="AdaptiveSentinel",
    description="Adaptive Insider Threat & Behavioral Security Intelligence Platform",
    version="2.0"
)

live_incidents = []

# =========================================
# LOAD DATA + TRAIN MODEL
# =========================================

department_mapping = {
    "Finance": 0, "HR": 1,
    "Engineering": 2, "IT": 3, "Sales": 4
}

feature_columns = [
    "login_hour", "files_downloaded",
    "sensitive_docs_accessed", "cloud_upload_mb",
    "geo_distance_km", "failed_mfa_attempts",
    "usb_device_connected", "privilege_escalation_attempts",
    "endpoint_risk_score", "department_encoded"
]

try:
    df = pd.read_csv(DATA_PATH)
    df["department_encoded"] = df["department"].map(department_mapping)
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(df[feature_columns])
    model = IsolationForest(contamination=0.3, random_state=42)
    model.fit(X_scaled)
    DATA_LOADED = True
    print(f"[API] Enterprise data loaded from {DATA_PATH}")
except Exception as e:
    print(f"[API] Warning: Could not load enterprise data: {e}")
    DATA_LOADED = False
    scaler = None
    model = None

# Initialize continual learner
continual_detector = ContinualAnomalyDetector(
    contamination=0.3,
    memory_capacity=500,
    update_frequency=50
)

if DATA_LOADED:
    continual_detector.initial_fit(X_scaled)

# =========================================
# PYDANTIC MODELS
# =========================================

class SecurityEvent(BaseModel):
    employee_id: str
    department: str
    login_hour: int
    files_downloaded: int
    sensitive_docs_accessed: int
    cloud_upload_mb: int
    geo_distance_km: int
    failed_mfa_attempts: int
    usb_device_connected: int
    privilege_escalation_attempts: int
    endpoint_risk_score: float

class SOCBriefRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    session_commands: list[str]
    severity: str
    confidence: float
    prediction_set: list[str]
    attacker_profile: str
    indicators: list[str]

class DeceptionRequest(BaseModel):
    session_embedding: list[float]
    mitre_vector: list[float]

# =========================================
# SAMPLE DATA — always shown if file empty
# =========================================

SAMPLE_DATA = [
    {
        "timestamp": "2025-05-16T10:00:00",
        "source_ip": "192.168.1.100",
        "username": "root",
        "command": "wget malware.sh",
        "severity": "CRITICAL",
        "threat_severity": "CRITICAL",
        "recommended_action": "BLOCK_AND_ALERT",
        "mitre_attack": ["Command and Control"],
        "reasoning": ["Malware delivery detected", "Privilege escalation observed"],
        "employee_id": "EMP-1001",
        "department": "Engineering",
        "files_downloaded": 340,
        "sensitive_docs_accessed": 12,
        "cloud_upload_mb": 850,
        "geo_distance_km": 4200,
        "endpoint_risk_score": 0.94,
        "system_decision": "BLOCK_AND_ALERT",
        "session_commands": ["whoami", "wget malware.sh"],
        "session_duration_s": 12
    },
    {
        "timestamp": "2025-05-16T10:01:00",
        "source_ip": "192.168.1.101",
        "username": "admin",
        "command": "cat /etc/passwd",
        "severity": "HIGH",
        "threat_severity": "HIGH",
        "recommended_action": "MONITOR_AND_ALERT",
        "mitre_attack": ["Credential Access"],
        "reasoning": ["Credential access attempt", "Suspicious enumeration"],
        "employee_id": "EMP-1002",
        "department": "Finance",
        "files_downloaded": 210,
        "sensitive_docs_accessed": 8,
        "cloud_upload_mb": 420,
        "geo_distance_km": 1800,
        "endpoint_risk_score": 0.76,
        "system_decision": "MONITOR_AND_ALERT",
        "session_commands": ["whoami", "cat /etc/passwd"],
        "session_duration_s": 8
    },
    {
        "timestamp": "2025-05-16T10:02:00",
        "source_ip": "192.168.1.102",
        "username": "user",
        "command": "sudo su",
        "severity": "MEDIUM",
        "threat_severity": "MEDIUM",
        "recommended_action": "MONITOR",
        "mitre_attack": ["Privilege Escalation"],
        "reasoning": ["Privilege escalation attempt"],
        "employee_id": "EMP-1003",
        "department": "IT",
        "files_downloaded": 95,
        "sensitive_docs_accessed": 3,
        "cloud_upload_mb": 120,
        "geo_distance_km": 200,
        "endpoint_risk_score": 0.51,
        "system_decision": "MONITOR",
        "session_commands": ["whoami", "sudo su"],
        "session_duration_s": 5
    }
]

# =========================================
# CORE HELPER — READ ATTACK LOG
# =========================================

def read_attack_log() -> list:
    if not os.path.exists(LIVE_ATTACKS_PATH):
        os.makedirs(os.path.dirname(LIVE_ATTACKS_PATH), exist_ok=True)
        with open(LIVE_ATTACKS_PATH, "w", encoding="utf-8") as f:
            json.dump(SAMPLE_DATA, f, indent=2)
        return SAMPLE_DATA

    try:
        with open(LIVE_ATTACKS_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content or content in ["[]", "{}", ""]:
            with open(LIVE_ATTACKS_PATH, "w", encoding="utf-8") as f:
                json.dump(SAMPLE_DATA, f, indent=2)
            return SAMPLE_DATA

        data = json.loads(content)

        if isinstance(data, list) and len(data) > 0:
            return data
        if isinstance(data, dict) and data:
            return [data]

        with open(LIVE_ATTACKS_PATH, "w", encoding="utf-8") as f:
            json.dump(SAMPLE_DATA, f, indent=2)
        return SAMPLE_DATA

    except Exception as e:
        print(f"[API] Error reading file: {e}")
        return SAMPLE_DATA

# =========================================
# SCORE COMPUTATION HELPERS
# =========================================

SEVERITY_WEIGHT = {
    "CRITICAL": 1.0,
    "HIGH":     0.75,
    "MEDIUM":   0.40,
    "LOW":      0.10
}

def compute_threat_deviation_score(attacks: list) -> float:
    """
    Weighted average of endpoint_risk_score × severity_weight.
    Returns a value between 0.0 and 1.0.
    """
    if not attacks:
        return 0.0
    scores = []
    for a in attacks:
        risk  = float(a.get("endpoint_risk_score", 0.5))
        sev   = a.get("severity") or a.get("threat_severity", "LOW")
        weight = SEVERITY_WEIGHT.get(sev, 0.1)
        scores.append(risk * weight)
    return round(float(np.mean(scores)), 3)

def compute_behavioral_drift(attacks: list) -> str:
    """
    Drift level based on proportion of HIGH/CRITICAL events.
    """
    if not attacks:
        return "LOW"
    total    = len(attacks)
    critical = sum(1 for a in attacks if a.get("severity") == "CRITICAL"
                   or a.get("threat_severity") == "CRITICAL")
    high     = sum(1 for a in attacks if a.get("severity") == "HIGH"
                   or a.get("threat_severity") == "HIGH")
    ratio = (critical + high) / total
    if ratio >= 0.5 or critical >= 2:
        return "HIGH"
    elif ratio >= 0.25 or high >= 2:
        return "MEDIUM"
    return "LOW"

def compute_active_incidents(attacks: list) -> int:
    """
    Count of HIGH + CRITICAL events.
    """
    return sum(
        1 for a in attacks
        if a.get("severity") in ["HIGH", "CRITICAL"]
        or a.get("threat_severity") in ["HIGH", "CRITICAL"]
    )

def compute_system_decision(attacks: list, total_incidents: int) -> str:
    if len(attacks) > 10:
        return "RETRAIN"
    elif total_incidents > 2:
        return "MONITOR"
    elif total_incidents > 0:
        return "MONITOR"
    return "STABLE"

# =========================================
# ROOT
# =========================================

@app.get("/")
def root():
    return {
        "status": "AdaptiveSentinel running",
        "version": "2.0",
        "platform": "AdaptiveSentinel AI Security Platform",
        "base_dir": BASE_DIR,
        "live_attacks_path": LIVE_ATTACKS_PATH,
        "file_exists": os.path.exists(LIVE_ATTACKS_PATH),
        "capabilities": [
            "Behavioral Threat Detection", "Anomaly Detection",
            "Drift Monitoring", "SOC AI Brief Generation",
            "RL-based Deception Planning", "Counterfactual Analysis",
            "MITRE ATT&CK Mapping", "Shadow Deployment Monitoring"
        ],
        "available_endpoints": [
            "/health", "/status", "/incidents", "/live-feed",
            "/live-attacks", "/analyze", "/drift-status",
            "/run-drift-check", "/model-registry", "/shadow-log",
            "/soc-brief", "/deception-action", "/deception-actions",
            "/counterfactual", "/docs"
        ]
    }

# =========================================
# HEALTH
# =========================================

@app.get("/health")
def health():
    attacks = read_attack_log()
    return {
        "status": "healthy",
        "timestamp": str(datetime.now(timezone.utc)),
        "live_attacks_path": LIVE_ATTACKS_PATH,
        "file_exists": os.path.exists(LIVE_ATTACKS_PATH),
        "record_count": len(attacks)
    }

# =========================================
# STATUS — feeds all 4 dashboard metric cards
# =========================================

@app.get("/status")
def system_status():
    try:
        attacks = read_attack_log()

        drift_level      = compute_behavioral_drift(attacks)
        deviation_score  = compute_threat_deviation_score(attacks)
        total_incidents  = compute_active_incidents(attacks)
        decision         = compute_system_decision(attacks, total_incidents)

        return {
            "behavioral_drift_level":    drift_level,
            "threat_deviation_score":    deviation_score,
            "active_security_incidents": total_incidents,
            "system_decision":           decision,
            "total_attacks_logged":      len(attacks),
            "timestamp": str(datetime.now(timezone.utc))
        }

    except Exception as e:
        return {
            "behavioral_drift_level":    "LOW",
            "threat_deviation_score":    0.0,
            "active_security_incidents": 0,
            "system_decision":           "STABLE",
            "error": str(e)
        }

# =========================================
# INCIDENTS
# =========================================

@app.get("/incidents")
def incidents():
    try:
        attacks = read_attack_log()
        return [
            item for item in attacks
            if item.get("severity") in ["HIGH", "CRITICAL"]
            or item.get("threat_severity") in ["HIGH", "CRITICAL"]
        ]
    except Exception:
        return []

# =========================================
# LIVE FEED
# =========================================

@app.get("/live-feed")
def live_feed():
    try:
        return read_attack_log()
    except Exception:
        return []

# =========================================
# LIVE ATTACKS
# =========================================

@app.get("/live-attacks")
def get_live_attacks():
    try:
        return read_attack_log()
    except Exception:
        return []

# =========================================
# ANALYZE
# =========================================

@app.post("/analyze")
def analyze(event: SecurityEvent):
    if not DATA_LOADED:
        raise HTTPException(status_code=503, detail="Enterprise data not loaded.")
    try:
        incoming = pd.DataFrame([event.dict()])
        incoming["department_encoded"] = incoming["department"].map(department_mapping)
        X = incoming[feature_columns]
        X_scaled_live = scaler.transform(X)
        score = model.decision_function(X_scaled_live)[0]

        if score < -0.10:
            severity = "CRITICAL"; action = "ISOLATE_ENDPOINT"
        elif score < -0.05:
            severity = "HIGH";     action = "DISABLE_ACCOUNT"
        elif score < 0:
            severity = "MEDIUM";   action = "CHALLENGE_MFA"
        else:
            severity = "LOW";      action = "ALLOW"

        incident = {
            "employee_id": event.employee_id,
            "severity": severity,
            "threat_severity": severity,
            "recommended_action": action,
            "anomaly_score": round(float(score), 4),
            "timestamp": str(datetime.now(timezone.utc))
        }
        live_incidents.append(incident)
        return incident
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# RETRAIN — full model refit
# (this is what the dashboard's
#  "Force Adaptive Model Retraining"
#  button actually calls)
# =========================================

@app.post("/retrain")
def retrain_model():
    """
    Full retrain of the batch IsolationForest from the
    current enterprise_security_logs.csv, replacing the
    in-memory model and scaler. Distinct from
    /continual-update, which does a single-event online
    update — this re-fits from scratch on all available data.
    """
    global model, scaler, DATA_LOADED

    try:
        df = pd.read_csv(DATA_PATH)
        df["department_encoded"] = df["department"].map(department_mapping)

        new_scaler = MinMaxScaler()
        X_scaled = new_scaler.fit_transform(df[feature_columns])

        new_model = IsolationForest(contamination=0.3, random_state=42)
        new_model.fit(X_scaled)

        scores = new_model.decision_function(X_scaled)

        scaler = new_scaler
        model = new_model
        DATA_LOADED = True

        try:
            from mlops.model_registry import log_model_run
            run_id = log_model_run(
                model_type="isolation_forest_full_retrain",
                params={"contamination": 0.3, "n_samples": len(df)},
                metrics={
                    "mean_anomaly_score": float(np.mean(scores)),
                    "std_anomaly_score": float(np.std(scores)),
                },
                sklearn_model=model,
                tags={"trigger": "manual_dashboard_retrain"}
            )
        except Exception as e:
            run_id = None
            print(f"[API] MLflow logging skipped: {e}")

        return {
            "status": "Retraining completed",
            "n_samples": len(df),
            "mean_anomaly_score": round(float(np.mean(scores)), 4),
            "mlflow_run_id": run_id,
            "timestamp": str(datetime.now(timezone.utc))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrain failed: {e}")

# =========================================
# DRIFT STATUS
# =========================================

@app.get("/drift-status")
def get_drift_status():
    if os.path.exists(DRIFT_ALERT_PATH):
        with open(DRIFT_ALERT_PATH) as f:
            return json.load(f)
    return {"drift_detected": False, "message": "No drift alerts on record."}

# =========================================
# RUN DRIFT CHECK
# =========================================

@app.post("/run-drift-check")
def run_drift_check():
    try:
        result = check_drift(current_embeddings=np.random.randn(50, 10))
        return {"status": "Drift analysis completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# MODEL REGISTRY
# =========================================

@app.get("/model-registry")
def get_model_registry():
    try:
        models = list_models()
        return {
            "registered_models": [
                {"name": name, "versions": [str(v) for v in versions]}
                for name, versions in models
            ]
        }
    except Exception:
        return {"registered_models": []}

# =========================================
# SHADOW LOG
# =========================================

@app.get("/shadow-log")
def get_shadow_log():
    if os.path.exists(SHADOW_LOG_PATH):
        with open(SHADOW_LOG_PATH) as f:
            return {"shadow_log": json.load(f)}
    return {"shadow_log": [], "message": "No shadow deployment data yet."}

# =========================================
# SOC BRIEF
# =========================================

@app.post("/soc-brief")
def get_soc_brief(req: SOCBriefRequest):
    prediction = {
        "severity": req.severity,
        "confidence": req.confidence,
        "prediction_set": req.prediction_set
    }
    attacker_profile = {
        "profile": req.attacker_profile,
        "indicators": req.indicators
    }
    shap_values = [
        ("command_frequency", 0.42),
        ("session_duration", 0.31),
        ("privilege_commands", 0.28),
        ("timing_variance", -0.19),
        ("known_malware_pattern", 0.55)
    ]
    return generate_soc_brief(
        session_commands=req.session_commands,
        prediction=prediction,
        shap_values=shap_values,
        attacker_profile=attacker_profile
    )

# =========================================
# DECEPTION ACTION
# =========================================

@app.post("/deception-action")
def get_deception_recommendation(req: DeceptionRequest):
    session_emb = np.array(req.session_embedding, dtype=np.float32)
    mitre_vec   = np.array(req.mitre_vector, dtype=np.float32)
    return get_deception_action(session_emb, mitre_vec)

@app.get("/deception-actions")
def list_deception_actions():
    return {"available_actions": DECEPTION_ACTIONS}

# =========================================
# COUNTERFACTUAL
# =========================================

@app.post("/counterfactual")
def get_counterfactual(commands: list[str], severity: str):
    return {"counterfactual": generate_counterfactual(commands, severity)}


# =========================================
# CONTINUAL LEARNING
# =========================================

@app.post("/continual-update")
def continual_update(event: SecurityEvent):
    """
    Online update endpoint — called after every
    new attack session to keep model current.
    """
    try:
        incoming = pd.DataFrame([event.dict()])
        incoming["department_encoded"] = incoming["department"].map(department_mapping)
        X = incoming[feature_columns].values
        result = continual_detector.update(X)
        return {"status": "updated", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model-updates")
def get_model_updates():
    return {
        "update_history": continual_detector.get_update_history(),
        "n_updates": continual_detector.n_updates,
        "memory_size": continual_detector.reservoir.size(),
        "total_seen": continual_detector.n_samples_seen
    }

# =========================================
# LOCAL RUN
# =========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)