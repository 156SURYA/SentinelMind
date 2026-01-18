# 🔐 AdaptiveSentinel — Adaptive SOC ML System

AdaptiveSentinel is an **end-to-end adaptive security monitoring system** that combines **machine learning**, **FastAPI**, **Streamlit**, and **Docker** to simulate a real-world **Security Operations Center (SOC)** workflow.

The system continuously monitors activity signals, detects anomalies and drift, triggers alerts, and decides whether retraining is required — all visualized through a live SOC dashboard.

---

## 🧠 Key Features

* 🔍 **Anomaly Detection** using ML models
* 📉 **Drift Monitoring** with automated decision logic
* 🚨 **Alert Management** and SOC-style visualization
* 🔁 **Automated Retraining Triggers**
* 🌐 **FastAPI Backend** for inference & system state
* 📊 **Streamlit Dashboard** for real-time monitoring
* 🐳 **Fully Dockerized** with multi-service orchestration

---

## 🏗️ Architecture Overview

```
+---------------------+        Docker Network        +---------------------+
|  Streamlit Dashboard|  <-----------------------> |   FastAPI Backend   |
|  (SOC Interface)    |      http://api:8000        |  (ML + Alerts)      |
|  Port: 8501         |                             |  Port: 8000         |
+---------------------+                             +---------------------+
```

* Services communicate via **Docker service discovery**
* No hard-coded localhost dependencies
* Production-style microservice separation

---

## 📁 Project Structure

```
AdaptiveSentinel/
│
├── api/                # FastAPI backend
│   └── main.py
│
├── dashboard/          # Streamlit SOC dashboard
│   └── app.py
│
├── honeypot/           # Simulated attack signals
├── honeylog/           # Security logs
├── data/               # Data & artifacts
│
├── Dockerfile          # API Dockerfile
├── docker-compose.yml  # Multi-service orchestration
├── requirements.txt
└── README.md
```

---

## 🚀 Run Locally (Docker Required)

### 1️⃣ Build & start the system

```bash
docker-compose up --build
```

### 2️⃣ Open in browser

| Component          | URL                                                          |
| ------------------ | ------------------------------------------------------------ |
| SOC Dashboard      | [http://localhost:8501](http://localhost:8501)               |
| API Health         | [http://localhost:8000/health](http://localhost:8000/health) |
| API Docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs)     |

### 3️⃣ Stop the system

```bash
Ctrl + C
```

(Optional cleanup)

```bash
docker-compose down
```

---

## 🧪 Example API Response

```json
{
  "drift_level": "LOW",
  "drift_score": 0.0,
  "avg_anomaly_score": 0.0,
  "alerts_active": 0,
  "system_decision": "STABLE"
}
```

---

## 🎯 Why This Project Matters

This project demonstrates:

* Real-world **ML system design**
* **MLOps & DevOps** fundamentals
* Docker-based **microservice architecture**
* SOC-style security monitoring concepts
* Production-oriented thinking beyond notebooks

---

## 📌 Tech Stack

* Python 3.10
* FastAPI
* Streamlit
* Scikit-learn
* Docker & Docker Compose

---

## 📜 License

This project is for educational and portfolio purposes.
