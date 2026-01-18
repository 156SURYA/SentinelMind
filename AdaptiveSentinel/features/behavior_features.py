import pandas as pd

# ---------------- CONFIG ----------------
TIME_COL = "time"
WINDOW_SECONDS = 60

FEATURE_COLUMNS = [
    "pass_len",
    "user_len",
    "is_long_pass",
    "is_short_user",
    "requests_last_min",
    "unique_users_last_min",
]


def extract_behavior_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Shared feature engineering for:
    - FastAPI inference
    - Offline pipelines
    """

    # -------- Normalize timestamp --------
    if "timestamp" in df.columns and TIME_COL not in df.columns:
        df[TIME_COL] = pd.to_datetime(df["timestamp"], utc=True)

    if TIME_COL not in df.columns:
        raise ValueError("Missing required field: time")

    # -------- Normalize fields --------
    df["user"] = df.get("username", df.get("user", "")).fillna("")
    df["password"] = df.get("password", "").fillna("")

    # -------- Basic features --------
    df["pass_len"] = df["password"].str.len().astype(int)
    df["user_len"] = df["user"].str.len().astype(int)

    df["is_long_pass"] = (df["pass_len"] > 12).astype(int)
    df["is_short_user"] = (df["user_len"] < 4).astype(int)

    # -------- Temporal features --------
    df = df.sort_values(TIME_COL).reset_index(drop=True)
    times = df[TIME_COL]

    reqs, uniqs = [], []

    for i in range(len(df)):
        t = times.iloc[i]
        window = df[
            (df[TIME_COL] > t - pd.Timedelta(seconds=WINDOW_SECONDS)) &
            (df[TIME_COL] <= t)
        ]
        reqs.append(len(window))
        uniqs.append(window["user"].nunique())

    df["requests_last_min"] = reqs
    df["unique_users_last_min"] = uniqs

    # -------- Return feature matrix --------
    return df[FEATURE_COLUMNS].fillna(0)
