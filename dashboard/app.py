import plotly.express as px
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
import ast

# =========================================
# PAGE CONFIG
# =========================================

st.set_page_config(
    page_title="AdaptiveSentinel SOC",
    layout="wide"
)

# =========================================
# API CONFIG
# =========================================

API_BASE = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"
)

# =========================================
# SAFE API REQUEST
# =========================================

def safe_get(endpoint):

    try:

        response = requests.get(
            f"{API_BASE}/{endpoint}"
        )

        return response.json()

    except Exception:

        return {}

# =========================================
# API HELPERS
# =========================================

def get_status():

    return safe_get("status")

def get_incidents():

    return safe_get("incidents")

def get_live_feed():

    return safe_get("live-feed")

def get_live_attacks():

    return safe_get("live-attacks")

def trigger_retrain():

    try:

        response = requests.post(
            f"{API_BASE}/retrain"
        )

        return response.json()

    except Exception:

        return {
            "status": "Retraining failed"
        }

# =========================================
# CUSTOM METRIC CARDS
# =========================================

def metric_card(title, value, color):

    st.markdown(
        f"""
        <div style="
            background-color:{color};
            padding:20px;
            border-radius:14px;
            text-align:center;
            color:white;
            font-weight:bold;
            box-shadow:0px 0px 12px rgba(0,0,0,0.2);
        ">
            <div style="
                font-size:16px;
                margin-bottom:10px;
            ">
                {title}
            </div>

            <div style="
                font-size:28px;
            ">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================
# TITLE
# =========================================

st.title("🛡️ AdaptiveSentinel")

st.subheader(
    "AI-Powered Insider Threat & Behavioral Security Intelligence Platform"
)

st.caption(
    "Enterprise Security Operations Center (SOC) Console"
)

# =========================================
# LOAD API DATA
# =========================================

status = get_status()

incidents = get_incidents()

live_feed = get_live_feed()

live_attacks = get_live_attacks()

incident_df = pd.DataFrame(incidents)

live_df = pd.DataFrame(live_feed)

attack_df = pd.DataFrame(live_attacks)

# =========================================
# TOP METRICS
# =========================================

st.divider()

col1, col2, col3, col4 = st.columns(4)

drift_level = status.get(
    "behavioral_drift_level",
    "LOW"
)

decision = status.get(
    "system_decision",
    "STABLE"
)

# =========================================
# COLORS
# =========================================

drift_color = {

    "HIGH": "#ff4b4b",

    "MEDIUM": "#ffa500",

    "LOW": "#4caf50"

}.get(drift_level, "#4caf50")

decision_color = {

    "RETRAIN": "#ff4b4b",

    "MONITOR": "#ffa500",

    "STABLE": "#4caf50"

}.get(decision, "#4caf50")

# =========================================
# METRIC CARDS
# =========================================

with col1:

    metric_card(
        "Behavioral Drift",
        drift_level,
        drift_color
    )

with col2:

    metric_card(
        "Threat Deviation Score",
        round(
            status.get(
                "threat_deviation_score",
                0
            ),
            3
        ),
        "#1f77b4"
    )

with col3:

    metric_card(
        "Active Security Incidents",
        status.get(
            "active_security_incidents",
            0
        ),
        "#6a1b9a"
    )

with col4:

    metric_card(
        "Adaptive System Decision",
        decision,
        decision_color
    )

# =========================================
# ACTIVE INCIDENTS
# =========================================

st.divider()

st.subheader(
    "🚨 Active Insider Threat Incidents"
)

if not incident_df.empty:

    display_columns = [

        "employee_id",

        "department",

        "files_downloaded",

        "sensitive_docs_accessed",

        "cloud_upload_mb",

        "geo_distance_km",

        "endpoint_risk_score",

        "threat_severity",

        "system_decision"
    ]

    st.dataframe(
        incident_df[display_columns],
        use_container_width=True
    )

else:

    st.success(
        "No active insider threat incidents detected."
    )

# =========================================
# LIVE FEED
# =========================================

st.divider()

st.subheader(
    "📡 Real-Time Endpoint Threat Feed"
)

if not live_df.empty:

    feed_columns = [

        "timestamp",

        "employee_id",

        "department",

        "files_downloaded",

        "cloud_upload_mb",

        "endpoint_risk_score",

        "threat_severity",

        "recommended_action"
    ]

    st.dataframe(
        live_df[feed_columns],
        use_container_width=True
    )

else:

    st.info(
        "Waiting for live endpoint telemetry..."
    )

# =========================================
# LIVE ATTACKER INTELLIGENCE
# =========================================

st.divider()

st.subheader(
    "🛡️ Live Attacker Intelligence Feed"
)

if not attack_df.empty:

    attack_columns = [

        "timestamp",

        "source_ip",

        "username",

        "command",

        "severity",

        "recommended_action"
    ]

    available_columns = [

        col for col in attack_columns
        if col in attack_df.columns
    ]

    st.dataframe(

        attack_df[available_columns],

        use_container_width=True,

        height=400
    )

    # =====================================
    # CRITICAL THREAT ALERTS
    # =====================================

    critical_attacks = attack_df[
        attack_df["severity"] == "CRITICAL"
    ]

    if len(critical_attacks) > 0:

        st.error(
            f"🚨 {len(critical_attacks)} "
            f"CRITICAL ATTACKS DETECTED"
        )

        for _, row in critical_attacks.iterrows():

            st.markdown(
                f"""
### 🚨 Critical Attacker Activity

- Source IP: `{row['source_ip']}`
- Username: `{row['username']}`
- Command: `{row['command']}`
- Response Action: `{row['recommended_action']}`
"""
            )

else:

    st.success(
        "✅ No attacker activity detected"
    )

# =========================================
# AI THREAT INTELLIGENCE
# =========================================

st.divider()

st.subheader(
    "🧠 AI Threat Intelligence Summaries"
)

if not live_df.empty:

    high_risk = live_df[
        live_df["threat_severity"].isin(
            ["HIGH", "CRITICAL", "MEDIUM"]
        )
    ]

    if not high_risk.empty:

        for _, row in high_risk.head(5).iterrows():

            reasoning_text = ""

            if "reasoning" in row:

                reasoning_value = row["reasoning"]

                if isinstance(reasoning_value, str):

                    try:

                        parsed = ast.literal_eval(
                            reasoning_value
                        )

                        if isinstance(parsed, list):

                            reasoning_text = "\n".join(
                                [
                                    f"• {r}"
                                    for r in parsed
                                ]
                            )

                        else:

                            reasoning_text = reasoning_value

                    except Exception:

                        reasoning_text = reasoning_value

                elif isinstance(reasoning_value, list):

                    reasoning_text = "\n".join(
                        [
                            f"• {r}"
                            for r in reasoning_value
                        ]
                    )

            st.warning(

                f"""
🚨 Threat detected for employee {row['employee_id']}

Department: {row['department']}

Behavior Summary:
• Downloaded {row['files_downloaded']} files
• Uploaded {row['cloud_upload_mb']} MB externally
• Endpoint risk score: {row['endpoint_risk_score']}

AI Reasoning:
{reasoning_text}

Recommended Response:
{row['recommended_action']}
"""
            )

# =========================================
# LIVE SOC ANALYTICS
# =========================================

st.divider()

st.subheader(
    "📊 Live Behavioral Security Analytics"
)

if not live_df.empty:

    severity_counts = live_df[
        "threat_severity"
    ].value_counts().reset_index()

    severity_counts.columns = [
        "Threat Severity",
        "Count"
    ]

    fig1 = px.bar(

        severity_counts,

        x="Threat Severity",

        y="Count",

        title="Threat Severity Distribution"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    fig2 = px.line(

        live_df.head(20),

        y="cloud_upload_mb",

        title="External Cloud Upload Activity"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    fig3 = px.scatter(

        live_df.head(20),

        x="files_downloaded",

        y="endpoint_risk_score",

        color="threat_severity",

        title="Endpoint Risk vs Download Volume"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

else:

    st.info(
        "Waiting for live telemetry analytics..."
    )

# =========================================
# RETRAINING
# =========================================

st.divider()

st.subheader(
    "🔁 Adaptive ML Operations"
)

if st.button(
    "Force Adaptive Model Retraining"
):

    with st.spinner(
        "Retraining behavioral intelligence model..."
    ):

        result = trigger_retrain()

        st.success(
            result.get(
                "status",
                "Retraining completed"
            )
        )

# =========================================
# FOOTER
# =========================================

st.divider()

st.caption(
    f"AdaptiveSentinel SOC • Last refreshed at "
    f"{datetime.utcnow().strftime('%H:%M:%S')} UTC"
)

st.caption(
    "🔄 Keep endpoint sensors running for live telemetry streaming."
)