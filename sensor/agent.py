import requests
import random
import time

API_URL = "http://127.0.0.1:8000/analyze"

departments = [
    "Finance",
    "HR",
    "Engineering",
    "IT",
    "Sales"
]

# =========================================
# NORMAL EMPLOYEE BEHAVIOR
# =========================================

def normal_behavior():

    return {

        "employee_id": f"EMP-{random.randint(1000, 9999)}",

        "department": random.choice(departments),

        "login_hour": random.randint(8, 18),

        "files_downloaded": random.randint(20, 200),

        "sensitive_docs_accessed": random.randint(0, 5),

        "cloud_upload_mb": random.randint(5, 100),

        "geo_distance_km": random.randint(1, 20),

        "failed_mfa_attempts": random.randint(0, 1),

        "usb_device_connected": 0,

        "privilege_escalation_attempts": 0,

        "endpoint_risk_score": random.randint(5, 20)
    }

# =========================================
# INSIDER THREAT BEHAVIOR
# =========================================

def insider_threat_behavior():

    return {

        "employee_id": f"EMP-{random.randint(1000, 9999)}",

        "department": random.choice(departments),

        "login_hour": random.randint(1, 4),

        "files_downloaded": random.randint(12000, 25000),

        "sensitive_docs_accessed": random.randint(300, 900),

        "cloud_upload_mb": random.randint(5000, 15000),

        "geo_distance_km": random.randint(3000, 9000),

        "failed_mfa_attempts": random.randint(2, 6),

        "usb_device_connected": 1,

        "privilege_escalation_attempts": random.randint(2, 8),

        "endpoint_risk_score": random.randint(75, 100)
    }

# =========================================
# LIVE SENSOR LOOP
# =========================================

print("\n🛡️ Adaptive Endpoint Sensor Active...\n")

while True:

    # =====================================
    # RANDOMLY CHOOSE EVENT TYPE
    # =====================================

    if random.random() < 0.7:

        payload = normal_behavior()

    else:

        payload = insider_threat_behavior()

    try:

        response = requests.post(
            API_URL,
            json=payload
        )

        result = response.json()

        print("\n===================================")

        print(
            f"👤 Employee: {payload['employee_id']}"
        )

        print(
            f"📂 Files Downloaded: "
            f"{payload['files_downloaded']}"
        )

        print(
            f"☁️ Upload Volume: "
            f"{payload['cloud_upload_mb']} MB"
        )

        print(
            f"🧠 Threat Severity: "
            f"{result['threat_severity']}"
        )

        print(
            f"⚡ Recommended Action: "
            f"{result['recommended_action']}"
        )

        print(
            f"📊 Anomaly Score: "
            f"{result['anomaly_score']}"
        )

    except Exception as e:

        print(f"❌ Sensor Error: {e}")

    time.sleep(5)