import pandas as pd
from sklearn.ensemble import IsolationForest

DATA = "data/processed/log_features.csv"

df = pd.read_csv(DATA)

X = df[["user_len", "pass_len", "is_admin"]]

model = IsolationForest(contamination=0.2, random_state=42)
model.fit(X)

df["anomaly"] = model.predict(X)

print(df)
