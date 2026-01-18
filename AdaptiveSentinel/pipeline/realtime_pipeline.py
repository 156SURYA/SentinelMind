import time
import subprocess
from pathlib import Path

RAW_LOG = Path("data/raw/api_logs.jsonl")

def run_pipeline():
    print("🔄 New data detected — updating pipeline...")

    subprocess.run(["python", "features/normalize_logs.py"])
    subprocess.run(["python", "features/behavior_features.py"])
    subprocess.run(["python", "models/score_anomalies.py"])
    subprocess.run(["python", "monitoring/alert.py"])


if __name__ == "__main__":
    print("🚀 Starting real-time pipeline watcher...")
    last_size = 0

    while True:
        if RAW_LOG.exists():
            size = RAW_LOG.stat().st_size
            if size != last_size:
                last_size = size
                run_pipeline()
        time.sleep(2)
