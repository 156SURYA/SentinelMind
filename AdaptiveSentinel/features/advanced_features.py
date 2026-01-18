import json
import pandas as pd
from pathlib import Path
import math

BASE = Path(__file__).resolve().parents[1]
RAW_FILE = BASE / "data" / "raw" / "api_logs.jsonl"
OUT_FILE = BASE / "data" / "processed" / "advanced_features.csv"

def entropy(s):
    if not s:
        return 0
    probs = [s.count(c) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in probs)

def extract():
    rows = []
    with open(RAW_FILE) as f:
        for line in f:
            log = json.loads(line)
            payload = log.get("payload", {})
            user = str(payload.get("user", ""))
            pwd = str(payload.get("pass", ""))

            rows.append({
                "user_len": len(user),
                "pass_len": len(pwd),
                "user_entropy": entropy(user),
                "pass_entropy": entropy(pwd),
                "is_admin": int(user.lower() in ["admin", "root"]),
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUT_FILE}")

if __name__ == "__main__":
    extract()
