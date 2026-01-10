from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

# =====================
# Paths
# =====================
LATEST_PATH = Path("data/latest.csv")
BASELINE_PATH = Path("data/last_prices.csv")
CHANGES_PATH = Path("data/price_changes.csv")

# =====================
# Helpers
# =====================
def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)

# =====================
# Main
# =====================
def main():
    if not LATEST_PATH.exists():
        raise RuntimeError("latest.csv missing")

    latest = pd.read_csv(LATEST_PATH)

    required = {"player_id", "price"}
    if not required.issubset(latest.columns):
        raise RuntimeError("latest.csv missing required columns")

    baseline = safe_read_csv(BASELINE_PATH)

    # First ever run: establish baseline
    if baseline.empty:
        baseline = latest[["player_id", "price"]].copy()
        baseline.to_csv(BASELINE_PATH, index=False)
        print("🧠 Baseline created (no detection on first run)")
        return

    merged = latest.merge(
        baseline,
        on="player_id",
        how="left",
        suffixes=("_new", "_old")
    )

    changes = merged[merged["price_new"] != merged["price_old"]].copy()

    if changes.empty:
        print("ℹ️ No price changes detected")
        return

    now = datetime.now(timezone.utc).date().isoformat()

    changes["change"] = changes.apply(
        lambda r: "rise" if r["price_new"] > r["price_old"] else "fall",
        axis=1
    )

    out = changes[[
        "player_id",
        "price_old",
        "price_new",
        "change"
    ]].copy()

    out.insert(0, "date", now)

    # Append to history
    if CHANGES_PATH.exists():
        history = pd.read_csv(CHANGES_PATH)
        out = pd.concat([history, out], ignore_index=True)

    CHANGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(CHANGES_PATH, index=False)

    # Update baseline ONLY after detection
    latest[["player_id", "price"]].to_csv(BASELINE_PATH, index=False)

    print(f"💸 Recorded {len(changes)} price changes")

if __name__ == "__main__":
    main()
