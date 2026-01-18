import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw/api_logs.jsonl")
OUT_PATH = Path("data/processed/normalized_logs.csv")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def main():
    records = []
    with open(RAW_PATH) as f:
        for line in f:
            records.append(pd.read_json(line, typ="series"))

    df = pd.DataFrame(records)

    df["time"] = pd.to_datetime(df["time"], unit="s")

    df = df.sort_values("time")

    df.to_csv(OUT_PATH, index=False)
    print(f"Saved normalized logs to {OUT_PATH}")

if __name__ == "__main__":
    main()
