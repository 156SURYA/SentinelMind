from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone
import pandas as pd

from AdaptiveSentinel.features.behavior_features import extract_behavior_features
from AdaptiveSentinel.models.score_anomalies import score_events
from AdaptiveSentinel.sentinel.health import get_system_health
from AdaptiveSentinel.monitoring.alert import get_active_alerts
from AdaptiveSentinel.pipeline.retrain_on_drift import retrain_if_needed

from pydantic import BaseModel, Field


# ================== Pydantic Models ==================

class PredictRequest(BaseModel):
    username: str = Field(..., example="surya123")
    password: str = Field(..., example="password123")
    timestamp: datetime = Field(..., example="2026-01-17T12:00:00Z")


class PredictResponse(BaseModel):
    pass_len: int
    user_len: int
    is_long_pass: int
    is_short_user: int
    requests_last_min: int
    unique_users_last_min: int

    anomaly_score: float
    status: str
    threat_score: float
    threat_level: str
    decision: str


# ================== APP ==================

app = FastAPI(
    title="AdaptiveSentinel",
    description="Adaptive Security ML System",
    version="1.0.0"
)
@app.get("/")
def root():
    return {
        "service": "AdaptiveSentinel",
        "status": "running",
        "message": "API is up"
    }



# ================== PREDICT ==================

@app.post("/predict", response_model=PredictResponse)
def predict(event: PredictRequest):
    try:
        # Convert request → DataFrame
        df = pd.DataFrame([event.dict()])

        # Normalize timestamp → time (feature contract)
        df["time"] = pd.to_datetime(df["timestamp"], utc=True)

        # Feature extraction + scoring
        features = extract_behavior_features(df)
        scored = score_events(features)

        return PredictResponse(**scored.iloc[0].to_dict())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================== HEALTH ==================

@app.get("/health")
def health():
    return get_system_health()


# ================== ALERTS ==================

@app.get("/alerts")
def alerts():
    return get_active_alerts()


# ================== MANUAL RETRAIN ==================

@app.post("/retrain")
def retrain():
    try:
        retrain_if_needed(force=True)
        return {"status": "retrain triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================== LOCAL RUN ==================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000)
