import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed" / "advanced_features.csv"
OUT = BASE / "data" / "processed" / "labeled_attacks.csv"

df = pd.read_csv(DATA)

def label(row):
    if row["is_admin"] and row["pass_len"] < 6:
        return 1  # brute force
    if row["pass_entropy"] > 2.5:
        return 2  # credential stuffing
    if row["user_len"] < 4 and row["pass_len"] < 4:
        return 3  # bot
    return 0  # normal

df["label"] = df.apply(label, axis=1)

df.to_csv(OUT, index=False)
print(df["label"].value_counts())
