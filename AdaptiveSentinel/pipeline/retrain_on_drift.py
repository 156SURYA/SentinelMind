from datetime import datetime
from pathlib import Path

from AdaptiveSentinel.sentinel.health import get_system_health
from AdaptiveSentinel.models.anomaly_detector import train_model


# ---------------- CONFIG ----------------
LOG_PATH = Path("data/processed/retrain_log.txt")


def retrain_if_needed(force: bool = False):
    """
    Retrain model if drift is detected OR if force=True
    """
    if force:
        print("🔁 Forced retraining triggered")
    else:
        print("🔍 Checking drift conditions")

    # existing retraining logic continues below

    """
    AdaptiveSentinel self-healing pipeline.
    Retrains the model only when system health requires it.
    """

    health = get_system_health()

    print("\n🧠 System Health Snapshot")
    print("-------------------------")
    for k, v in health.items():
        print(f"{k:18}: {v}")

    decision = health["system_decision"]

    if decision != "RETRAIN":
        print("\n✅ No retraining required. System is stable.")
        return

    print("\n🔁 RETRAINING TRIGGERED")

    try:
        train_model()

        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(
                f"{datetime.utcnow().isoformat()} | "
                f"RETRAIN | "
                f"drift_score={health['drift_score']} | "
                f"alerts={health['alerts_active']}\n"
            )

        print("✅ Retraining completed successfully.")
        print(f"📜 Logged to {LOG_PATH}")

    except Exception as e:
        print("❌ Retraining failed")
        print("Reason:", str(e))


# ---------------- CLI ENTRY ----------------
if __name__ == "__main__":
    retrain_if_needed()
