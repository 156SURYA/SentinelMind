from fastapi import FastAPI
from pydantic import BaseModel, Field
import json, time, traceback
from pathlib import Path

try:
    from models.anomaly_detector import score_request
except Exception as e:
    print("⚠️ Could not import anomaly detector:", e)
    score_request = None

app = FastAPI()

LOG_FILE = Path("data/raw/api_logs.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


class Login(BaseModel):
    user: str
    password: str = Field(..., alias="pass")

    class Config:
        allow_population_by_field_name = True


@app.post("/login")
def login(data: Login):
    event = {
        "time": time.time(),
        "user": data.user,
        "pass_len": len(data.password),
        "ip": "127.0.0.1"
    }

    # Log event
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

    anomaly_score = None

    if score_request is not None:
        try:
            anomaly_score = float(score_request(event))
        except Exception:
            print("⚠️ Scoring failed:")
            traceback.print_exc()

    return {"status": "ok", "anomaly_score": anomaly_score}
