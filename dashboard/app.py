import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ================= CONFIG =================
import os

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_URL = f"{API_BASE}/health"


st.set_page_config(
    page_title="AdaptiveSentinel SOC Dashboard",
    layout="wide"
)

# ================= HELPERS =================
def get_health():
    return requests.get(f"{API_BASE}/health").json()

def get_alerts():
    return requests.get(f"{API_BASE}/alerts").json()

def trigger_retrain():
    return requests.post(f"{API_BASE}/retrain").json()

def color_badge(label: str, value: str):
    colors = {
        "HIGH": "#ff4b4b",       # 🔴 Red
        "MEDIUM": "#ffa500",    # 🟠 Orange
        "LOW": "#4caf50",       # 🟢 Green
        "RETRAIN": "#ffa500",   # 🟠 Orange
        "MONITOR": "#ffcc00",   # 🟡 Yellow
        "STABLE": "#4caf50"     # 🟢 Green
    }

    color = colors.get(str(value).upper(), "#cccccc")

    st.markdown(
        f"""
        <div style="
            background-color:{color};
            padding:14px;
            border-radius:10px;
            text-align:center;
            font-weight:bold;
            font-size:18px;
            color:black;
        ">
            {label}<br>{value}
        </div>
        """,
        unsafe_allow_html=True
    )

# ================= TITLE =================
st.title("🔐 AdaptiveSentinel — SOC Dashboard")
st.caption("Real-time Adaptive Security ML System")

# ================= SYSTEM HEALTH =================
st.subheader("🧠 System Health")

health = get_health()

col1, col2, col3, col4 = st.columns(4)

with col1:
    color_badge("Drift Level", health.get("drift_level", "N/A"))

with col2:
    st.metric("Drift Score", round(health.get("drift_score", 0), 3))

with col3:
    st.metric("Active Alerts", health.get("alerts_active", 0))

with col4:
    color_badge("System Decision", health.get("system_decision", "N/A"))

st.divider()

# ================= ALERTS =================
st.subheader("🚨 Active Security Alerts")

alerts = get_alerts()

if alerts:
    df_alerts = pd.DataFrame(alerts)
    df_alerts["timestamp"] = pd.to_datetime(df_alerts["timestamp"])
    st.dataframe(df_alerts, use_container_width=True)
else:
    st.info("No active alerts 🎉")

st.divider()

# ================= MANUAL CONTROL =================
st.subheader("🔁 Manual Control")

if st.button("Force Retrain Model"):
    with st.spinner("Retraining model..."):
        result = trigger_retrain()
        st.success(result.get("status", "Retrain triggered"))

st.caption(f"Last refreshed at {datetime.utcnow().strftime('%H:%M:%S')} UTC")
