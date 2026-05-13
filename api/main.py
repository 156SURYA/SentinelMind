import json
from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone
import pandas as pd

from pydantic import BaseModel

from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest

# =========================================
# APP CONFIG
# =========================================

app = FastAPI(
    title="AdaptiveSentinel",
    description="Adaptive Insider Threat & Behavioral Security Intelligence Platform",
    version="4.0.0"
)

# =========================================
# DATA PATHS
# =========================================

DATA_PATH = "data/raw/enterprise_security_logs.csv"

# =========================================
# LIVE INCIDENT STORAGE
# =========================================

live_incidents = []

# =========================================
# LOAD DATA
# =========================================

df = pd.read_csv(DATA_PATH)

# =========================================
# DEPARTMENT ENCODING
# =========================================

department_mapping = {
    "Finance": 0,
    "HR": 1,
    "Engineering": 2,
    "IT": 3,
    "Sales": 4
}

df["department_encoded"] = df["department"].map(
    department_mapping
)

# =========================================
# FEATURE COLUMNS
# =========================================

feature_columns = [

    "login_hour",

    "files_downloaded",

    "sensitive_docs_accessed",

    "cloud_upload_mb",

    "geo_distance_km",

    "failed_mfa_attempts",

    "usb_device_connected",

    "privilege_escalation_attempts",

    "endpoint_risk_score",

    "department_encoded"
]

# =========================================
# NORMALIZATION
# =========================================

scaler = MinMaxScaler()

X_scaled = scaler.fit_transform(
    df[feature_columns]
)

# =========================================
# MODEL TRAINING
# =========================================

model = IsolationForest(
    contamination=0.3,
    random_state=42
)

model.fit(X_scaled)

# =========================================
# REQUEST MODEL
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

    endpoint_risk_score: int

# =========================================
# ROOT ENDPOINT
# =========================================

@app.get("/")
def root():

    return {

        "platform": "AdaptiveSentinel",

        "status": "operational",

        "capability":
            "Behavioral Security Intelligence"
    }

# =========================================
# HEALTH CHECK
# =========================================

@app.get("/health")
def health():

    return {

        "status": "healthy",

        "timestamp": str(
            datetime.now(timezone.utc)
        )
    }

# =========================================
# INCIDENT GENERATION
# =========================================

def generate_incidents():

    local_df = pd.read_csv(DATA_PATH)

    local_df["department_encoded"] = local_df[
        "department"
    ].map(department_mapping)

    X = local_df[feature_columns]

    X_scaled_local = scaler.transform(X)

    local_df["anomaly_prediction"] = model.predict(
        X_scaled_local
    )

    local_df["anomaly_score"] = model.decision_function(
        X_scaled_local
    )

    # =====================================
    # THREAT CLASSIFICATION
    # =====================================

    def classify(score):

        if score < -0.10:
            return "CRITICAL"

        elif score < -0.05:
            return "HIGH"

        elif score < 0:
            return "MEDIUM"

        else:
            return "LOW"

    local_df["threat_severity"] = local_df[
        "anomaly_score"
    ].apply(classify)

    # =====================================
    # RESPONSE ACTIONS
    # =====================================

    def response(level):

        if level == "CRITICAL":
            return "ISOLATE_ENDPOINT"

        elif level == "HIGH":
            return "DISABLE_ACCOUNT"

        elif level == "MEDIUM":
            return "CHALLENGE_MFA"

        else:
            return "ALLOW"

    local_df["system_decision"] = local_df[
        "threat_severity"
    ].apply(response)

    return local_df

# =========================================
# SYSTEM STATUS
# =========================================

@app.get("/status")
def system_status():

    scored_df = generate_incidents()

    avg_score = scored_df[
        "anomaly_score"
    ].mean()

    active_incidents = len(

        scored_df[
            scored_df["threat_severity"] != "LOW"
        ]
    )

    drift_score = abs(avg_score)

    if drift_score > 0.08:

        drift_level = "HIGH"

    elif drift_score > 0.04:

        drift_level = "MEDIUM"

    else:

        drift_level = "LOW"

    if drift_level == "HIGH":

        decision = "RETRAIN"

    elif drift_level == "MEDIUM":

        decision = "MONITOR"

    else:

        decision = "STABLE"

    return {

        "behavioral_drift_level":
            drift_level,

        "threat_deviation_score":
            round(drift_score, 3),

        "active_security_incidents":
            active_incidents,

        "system_decision":
            decision,

        "timestamp":
            str(datetime.now(timezone.utc))
    }

# =========================================
# INCIDENTS API
# =========================================

@app.get("/incidents")
def incidents():

    incident_df = generate_incidents()

    filtered = incident_df[
        incident_df["threat_severity"] != "LOW"
    ]

    return filtered.to_dict(
        orient="records"
    )

# =========================================
# LIVE FEED API
# =========================================

@app.get("/live-feed")
def live_feed():

    return list(
        reversed(live_incidents)
    )

# =========================================
# LIVE ANALYSIS
# =========================================

@app.post("/analyze")
def analyze(event: SecurityEvent):

    try:

        incoming = pd.DataFrame([
            event.dict()
        ])

        incoming["department_encoded"] = incoming[
            "department"
        ].map(department_mapping)

        X = incoming[feature_columns]

        X_scaled_live = scaler.transform(X)

        score = model.decision_function(
            X_scaled_live
        )[0]

        # =================================
        # THREAT SEVERITY
        # =================================

        if score < -0.10:

            severity = "CRITICAL"

            action = "ISOLATE_ENDPOINT"

        elif score < -0.05:

            severity = "HIGH"

            action = "DISABLE_ACCOUNT"

        elif score < 0:

            severity = "MEDIUM"

            action = "CHALLENGE_MFA"

        else:

            severity = "LOW"

            action = "ALLOW"

        # =================================
        # EXPLAINABLE AI REASONING
        # =================================

        reasoning = []

        if event.files_downloaded > 10000:

            reasoning.append(
                "Large file download spike detected"
            )

        if event.cloud_upload_mb > 5000:

            reasoning.append(
                "High external cloud upload activity"
            )

        if event.login_hour < 5:

            reasoning.append(
                "Abnormal off-hours access behavior"
            )

        if event.failed_mfa_attempts > 2:

            reasoning.append(
                "Multiple failed MFA attempts observed"
            )

        if event.privilege_escalation_attempts > 1:

            reasoning.append(
                "Suspicious privilege escalation attempts"
            )

        if event.endpoint_risk_score > 80:

            reasoning.append(
                "Endpoint risk score exceeds safe threshold"
            )

        if len(reasoning) == 0:

            reasoning.append(
                "Behavior within normal operational baseline"
            )

        # =================================
        # INCIDENT STORAGE
        # =================================

        incident = {

            "employee_id":
                event.employee_id,

            "department":
                event.department,

            "files_downloaded":
                event.files_downloaded,

            "sensitive_docs_accessed":
                event.sensitive_docs_accessed,

            "cloud_upload_mb":
                event.cloud_upload_mb,

            "endpoint_risk_score":
                event.endpoint_risk_score,

            "threat_severity":
                severity,

            "recommended_action":
                action,

            "reasoning":
                reasoning,

            "anomaly_score":
                round(float(score), 4),

            "timestamp":
                str(datetime.now(timezone.utc))
        }

        live_incidents.append(incident)

        # Keep only latest 50

        if len(live_incidents) > 50:

            live_incidents.pop(0)

        # =================================
        # RESPONSE
        # =================================

        return {

            "employee_id":
                event.employee_id,

            "anomaly_score":
                round(float(score), 4),

            "threat_severity":
                severity,

            "recommended_action":
                action,

            "reasoning":
                reasoning,

            "analysis_timestamp":
                str(datetime.now(timezone.utc))
        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )

# =========================================
# RETRAIN MODEL
# =========================================

@app.post("/retrain")
def retrain():

    global model

    refreshed_df = pd.read_csv(DATA_PATH)

    refreshed_df["department_encoded"] = refreshed_df[
        "department"
    ].map(department_mapping)

    X = refreshed_df[feature_columns]

    X_scaled_refresh = scaler.fit_transform(X)

    model = IsolationForest(

        contamination=0.3,

        random_state=42
    )

    model.fit(X_scaled_refresh)

    return {

        "status":
            "Adaptive model retrained successfully"
    }

# =========================================
# LOCAL RUN
# =========================================


# =========================================
# LIVE ATTACK FEED
# =========================================

@app.get("/live-attacks")
def live_attacks():

    try:

        with open(
            "honeypot/live_attacks.json",
            "r"
        ) as f:

            attacks = json.load(f)

        return attacks

    except Exception as e:

        return {
            "error": str(e)
        }
    
    
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "api.main:app",

        host="127.0.0.1",

        port=8000,

        reload=True
    )