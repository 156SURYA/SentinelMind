import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

# ==============================
# LOAD ENTERPRISE SECURITY LOGS
# ==============================

df = pd.read_csv("data/raw/enterprise_security_logs.csv")

# ==============================
# ENCODE CATEGORICAL FEATURES
# ==============================

dept_encoder = LabelEncoder()

df["department_encoded"] = dept_encoder.fit_transform(df["department"])

# ==============================
# FEATURES FOR ML PIPELINE
# ==============================

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

X = df[feature_columns]

# ==============================
# NORMALIZATION
# ==============================

scaler = MinMaxScaler()

X_scaled = scaler.fit_transform(X)

normalized_df = pd.DataFrame(X_scaled, columns=feature_columns)

# ==============================
# SAVE PROCESSED DATA
# ==============================

normalized_df.to_csv(
    "data/processed/enterprise_processed.csv",
    index=False
)

print("\n✅ Enterprise telemetry preprocessing complete.")
print("📁 Saved to: data/processed/enterprise_processed.csv")