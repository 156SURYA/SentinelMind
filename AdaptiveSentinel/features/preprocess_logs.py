import json
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RAW_FILE = BASE / "data" / "raw" / "api_logs.jsonl"
OUT_FILE = BASE / "data" / "processed" / "log_features.csv"

def extract_features():
    rows = []
    if not RAW_FILE.exists():
        print(f"Log file not found: {RAW_FILE}")
        return

    with open(RAW_FILE, "r") as f:
        for line in f:
            log = json.loads(line)
            payload = log.get("payload", {})
            rows.append({
                "ip": log.get("ip"),
                "user_len": len(str(payload.get("user", ""))),
                "pass_len": len(str(payload.get("pass", ""))),
                "is_admin": int(payload.get("user", "").lower() in ["admin", "root"]),
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUT_FILE}")

if __name__ == "__main__":
    extract_features()
