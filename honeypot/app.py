from fastapi import FastAPI
from pydantic import BaseModel, Field
import json, time, traceback
from pathlib import Path

try:
    from AdaptiveSentinel.models.anomaly_detector import score_request
    SCORER_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Could not import anomaly detector: {e}")
    score_request = None
    SCORER_AVAILABLE = False

app = FastAPI(title="AdaptiveSentinel — Login Anomaly Service")

LOG_FILE = Path("data/raw/api_logs.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


class Login(BaseModel):
    user: str
    password: str = Field(..., alias="pass")

    class Config:
        allow_population_by_field_name = True


class LoginResponse(BaseModel):
    status: str
    anomaly_score: float | None
    scorer_available: bool


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "scorer_available": SCORER_AVAILABLE,
        "log_file_exists": LOG_FILE.exists(),
    }


@app.post("/login", response_model=LoginResponse)
def login(data: Login):
    event = {
        "time": time.time(),
        "user": data.user,
        "pass_len": len(data.password),
        "ip": "127.0.0.1"
    }

    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to write log: {e}")

    anomaly_score = None

    if score_request is not None:
        try:
            anomaly_score = float(score_request(event))
        except Exception:
            print("⚠️ Scoring failed:")
            traceback.print_exc()

    return LoginResponse(
        status="ok",
        anomaly_score=anomaly_score,
        scorer_available=SCORER_AVAILABLE,
    )