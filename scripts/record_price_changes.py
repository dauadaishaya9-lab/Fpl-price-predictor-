from pathlib import Path
import pandas as pd
from datetime import date

# =====================
# Paths
# =====================
LATEST_PATH = Path("data/latest.csv")
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
        print("ℹ️ latest.csv missing, skipping price change detection")
        return

    latest = pd.read_csv(LATEST_PATH)

    required = {"player_id", "web_name", "now_cost"}
    if not required.issubset(latest.columns):
        raise RuntimeError("latest.csv missing required columns")

    latest = latest[["player_id", "web_name", "now_cost"]].copy()
    latest["date"] = date.today()

    history = safe_read_csv(CHANGES_PATH)

    # ---------------------
    # First run: bootstrap
    # ---------------------
    if history.empty:
        history = latest.rename(columns={"now_cost": "price"})
        history["change"] = "none"
        CHANGES_PATH.parent.mkdir(parents=True, exist_ok=True)
        history.to_csv(CHANGES_PATH, index=False)
        print("📘 Price history initialised")
        return

    # ---------------------
    # Compare vs last recorded prices
    # ---------------------
    last_prices = (
        history
        .sort_values("date")
        .drop_duplicates(subset=["player_id"], keep="last")
    )

    merged = latest.merge(
        last_prices[["player_id", "price"]],
        on="player_id",
        how="left"
    )

    merged["change"] = "none"
    merged.loc[merged["now_cost"] > merged["price"], "change"] = "rise"
    merged.loc[merged["now_cost"] < merged["price"], "change"] = "fall"

    changes = merged[merged["change"] != "none"].copy()

    if changes.empty:
        print("ℹ️ No price changes detected")
        return

    changes = changes.rename(columns={"now_cost": "price"})
    changes = changes[[
        "player_id",
        "web_name",
        "price",
        "change"
    ]]

    changes["date"] = date.today()

    # ---------------------
    # Append safely (idempotent)
    # ---------------------
    history = pd.concat([history, changes], ignore_index=True)

    history = (
        history
        .sort_values("date")
        .drop_duplicates(subset=["player_id", "date"], keep="last")
    )

    CHANGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(CHANGES_PATH, index=False)

    print(f"💰 Recorded {len(changes)} price changes")


if __name__ == "__main__":
    main()
