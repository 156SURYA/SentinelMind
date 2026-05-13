import pandas as pd
from sklearn.ensemble import IsolationForest

# ======================================
# LOAD ORIGINAL + PROCESSED DATA
# ======================================

raw_df = pd.read_csv("data/raw/enterprise_security_logs.csv")

processed_df = pd.read_csv(
    "data/processed/enterprise_processed.csv"
)

# ======================================
# TRAIN ISOLATION FOREST
# ======================================

model = IsolationForest(
    contamination=0.3,
    random_state=42
)

model.fit(processed_df)

# ======================================
# PREDICTIONS
# ======================================

raw_df["anomaly_prediction"] = model.predict(processed_df)

raw_df["anomaly_score"] = model.decision_function(processed_df)

# ======================================
# THREAT CLASSIFICATION
# ======================================

def classify_threat(score):

    if score < -0.10:
        return "CRITICAL"

    elif score < -0.05:
        return "HIGH"

    elif score < 0:
        return "MEDIUM"

    else:
        return "LOW"

raw_df["threat_severity"] = raw_df[
    "anomaly_score"
].apply(classify_threat)

# ======================================
# INCIDENT RESPONSE DECISION
# ======================================

def incident_response(level):

    if level == "CRITICAL":
        return "ISOLATE_ENDPOINT"

    elif level == "HIGH":
        return "DISABLE_ACCOUNT"

    elif level == "MEDIUM":
        return "CHALLENGE_MFA"

    else:
        return "ALLOW"

raw_df["system_decision"] = raw_df[
    "threat_severity"
].apply(incident_response)

# ======================================
# SAVE FINAL SCORED INCIDENTS
# ======================================

raw_df.to_csv(
    "data/processed/enterprise_threat_scored.csv",
    index=False
)

# ======================================
# SUMMARY
# ======================================

print("\n🚨 Enterprise Threat Detection Complete")

print(
    raw_df[
        [
            "employee_id",
            "files_downloaded",
            "cloud_upload_mb",
            "anomaly_score",
            "threat_severity",
            "system_decision"
        ]
    ]
)