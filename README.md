<div align="center">

# 🛡️ AdaptiveSentinel

### AI-Powered Insider Threat & Behavioral Security Intelligence Platform

An end-to-end adaptive SOC (Security Operations Center) system combining unsupervised anomaly detection, continual/online learning, a real SSH honeypot with LLM-driven analysis, and an RL-based deception engine — containerized, deployed, and fully verified in production.

[![Python](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7.svg)](https://render.com/)
[![License](https://img.shields.io/badge/license-Educational-lightgrey.svg)](#license)

**🔗 [Live API](https://adaptive-sentinel-api.onrender.com) · [Live Dashboard](https://adaptive-sentinel-dashboard.onrender.com) · [API Docs (Swagger)](https://adaptive-sentinel-api.onrender.com/docs) · [Repo](https://github.com/156SURYA/SentinelMind)**

> ⏳ Free-tier hosting: if the links have been idle, the first request may take 30–60 seconds to spin back up. This is expected — not a bug.

</div>

---

## 📖 Overview

AdaptiveSentinel simulates a production-style SOC: it watches employee/endpoint behavior for insider-threat signals, runs a real SSH honeypot to capture live attacker sessions, scores everything through an unsupervised anomaly model, and layers a full MLOps stack on top — continual learning, statistical drift detection, model registry, shadow deployment, conformal prediction, and an RL-based deception planner — with an LLM turning raw model output into analyst-readable briefs.

Every endpoint listed in this README has been **individually tested against the live deployment**, not just described. That distinction matters: this document reflects verified behavior, not aspiration.

---

## 🎥 Screenshots

![Dashboard Overview](media/01-dashboard-overview.png)
*SOC dashboard — behavioral drift, threat deviation score, active incidents, and system decision, with the live incident table below*

![Critical Alert Feed](media/02-critical-alert.png)
*Live attacker intelligence feed — real-time command classification with severity and recommended action*

![Retrain Metrics](media/03-retrain-metrics.png)
*Force-retrain in action — real samples used, mean anomaly score, and MLflow run ID*

![API Docs](media/04-api-docs.png)
*Full Swagger UI — all 18 live endpoints*

![Honeypot Server View](media/05-honeypot-server.png)
*SSH honeypot server terminal — live threat classification and MITRE ATT&CK mapping mid-session*

![Honeypot Client View](media/06-honeypot-client.png)
*Attacker's-eye view of the same SSH session*

![SOC Brief Output](media/07-soc-brief.png)
*LLM-generated SOC brief via Swagger, showing the mock-mode fallback response*

**For LinkedIn specifically** (which typically shows only 3-4 project images): use #1, #2, #5, and #8 — they tell the strongest visual story in the fewest images (working dashboard, real detected threat, real live attacker session, system design).

---

## 🏗️ Architecture

![AdaptiveSentinel Architecture](media/08-architecture.svg)

Three independent surfaces feed the same FastAPI core:
- **Sensor Agent** (`sensor/agent.py`) generates synthetic employee behavior (70% normal / 30% insider-threat) and posts it to `/analyze` — this is also why the model's `contamination` parameter is set to `0.3`, matching the simulator's known injection rate.
- **SSH Honeypot** (`honeypot/ssh_honeypot.py`) is a real Paramiko-based SSH server on port 2222 that captures live attacker sessions, classifies each command against MITRE ATT&CK categories, profiles the attacker, and predicts their next likely action.
- **Streamlit Dashboard** polls the FastAPI backend — confirmed working identically in both local Docker and the live Render deployment.

---

## 🚀 Live Deployment — Fully Verified

Every endpoint below was tested against the production URL on Render, not just locally.

| Endpoint | Method | Verified Result |
|---|---|---|
| `/` | GET | Platform info, capabilities, endpoint list |
| `/health` | GET | `{"status": "healthy", "record_count": 84, ...}` |
| `/status` | GET | Real drift level, threat score, incident count |
| `/incidents` | GET | HIGH/CRITICAL filtered events |
| `/live-feed` / `/live-attacks` | GET | Full attack log |
| `/analyze` | POST | Real severity + anomaly score (e.g. MEDIUM / -0.0125) |
| `/retrain` | POST | Real MLflow run logged (e.g. run ID c9c661d0...) |
| `/continual-update` | POST | Online learner update |
| `/model-updates` | GET | Continual learner update history |
| `/drift-status` | GET | Last recorded drift alert |
| `/run-drift-check` | POST | Evidently-based drift report (honest "no_baseline" on fresh deploy) |
| `/model-registry` | GET | Real MLflow-logged runs |
| `/shadow-log` | GET | Champion/challenger comparison log |
| `/soc-brief` | POST | LLM-generated analyst brief (mock-mode fallback verified live) |
| `/counterfactual` | POST | LLM-generated evasion analysis |
| `/deception-actions` | GET | List of 8 RL deception strategies |
| `/deception-action` | POST | Real PPO inference, verified: action_id 6, "expose_decoy_database" |
| `/docs` | GET | Interactive Swagger UI |

Both `/analyze` and `/continual-update` return a clean `422` with a helpful message for invalid input (e.g. an unrecognized department) rather than a raw stack trace — validated explicitly during testing.

---

## 🧠 Key Features

| Feature | Status |
|---|---|
| Unsupervised anomaly detection | ✅ Live — IsolationForest over 10 behavioral features |
| Continual / online learning | ✅ Live — reservoir sampling + KS-test drift detection, incremental retraining |
| Statistical drift monitoring | ✅ Live (internal, real KS-test) / ⚠️ `/run-drift-check`'s Evidently report currently runs on synthetic embeddings, not live session data |
| MLflow experiment tracking | ✅ Live — every retrain and update logged with a real run ID |
| Shadow deployment | ✅ Live pattern — champion/challenger with F1-based promotion |
| Conformal prediction | ✅ Live — MAPIE-based calibrated prediction sets |
| LLM-generated SOC briefs | ✅ Live, currently in mock mode (no ANTHROPIC_API_KEY configured on the hosted deployment — gracefully degrades to a templated response instead of failing) |
| RL-based deception planning | ✅ Live, verified inference — trained via PPO over a 270-dim state space; reward function is currently a simulated proxy, not live honeypot telemetry |
| Real SSH honeypot | ✅ Live — genuine Paramiko server capturing real sessions, not simulated |
| Real-time SOC dashboard | ✅ Live — 4 metric cards, live incident/attacker feeds, Plotly analytics |
| Fully Dockerized | ✅ Live — multi-service Compose orchestration |
| Deployed to production | ✅ Live on Render — every endpoint independently tested |

---

## 📁 Project Structure