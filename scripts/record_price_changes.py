from pathlib import Path
import pandas as pd
from datetime import datetime

# =====================
# Paths
# =====================
LAST_PRICES_PATH = Path("data/last_prices.csv")
PRICE_CHANGES_PATH = Path("data/price_changes.csv")

# =====================
# Helpers
# =====================
def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)

def now_utc():
    return datetime.utcnow().strftime("%Y-%m-%d")

# =====================
# Main
# =====================
def record_price_changes(current_snapshot: pd.DataFrame):
    """
    current_snapshot columns required:
    - player_id
    - price
    """

    if current_snapshot.empty:
        print("⚠️ Empty snapshot, nothing to do")
        return

    # Ensure types
    current_snapshot = current_snapshot.copy()
    current_snapshot["player_id"] = current_snapshot["player_id"].astype(int)
    current_snapshot["price"] = current_snapshot["price"].astype(int)

    # Load last known prices
    last_prices = safe_read_csv(LAST_PRICES_PATH)

    if last_prices.empty:
        # First run bootstrap
        bootstrap = current_snapshot[["player_id", "price"]].copy()
        bootstrap["last_seen_date"] = now_utc()

        LAST_PRICES_PATH.parent.mkdir(parents=True, exist_ok=True)
        bootstrap.to_csv(LAST_PRICES_PATH, index=False)

        print("🆕 Baseline prices initialized")
        return

    last_prices["player_id"] = last_prices["player_id"].astype(int)
    last_prices["last_price"] = last_prices["last_price"].astype(int)

    merged = current_snapshot.merge(
        last_prices,
        on="player_id",
        how="left"
    )

    changes = []

    for _, row in merged.iterrows():
        prev_price = row["last_price"]
        curr_price = row["price"]

        # New player edge case
        if pd.isna(prev_price):
            changes.append({
                "player_id": row["player_id"],
                "old_price": None,
                "new_price": curr_price,
                "change": "init",
                "date": now_utc()
            })
            continue

        if curr_price != prev_price:
            direction = "rise" if curr_price > prev_price else "fall"
            changes.append({
                "player_id": row["player_id"],
                "old_price": prev_price,
                "new_price": curr_price,
                "change": direction,
                "date": now_utc()
            })

    # Persist price changes
    if changes:
        changes_df = pd.DataFrame(changes)

        if PRICE_CHANGES_PATH.exists():
            existing = pd.read_csv(PRICE_CHANGES_PATH)
            changes_df = pd.concat([existing, changes_df], ignore_index=True)

        PRICE_CHANGES_PATH.parent.mkdir(parents=True, exist_ok=True)
        changes_df.to_csv(PRICE_CHANGES_PATH, index=False)

        print(f"📈 Recorded {len(changes)} price change(s)")
    else:
        print("😴 No price changes detected")

    # Update baseline prices
    updated_last_prices = current_snapshot[["player_id", "price"]].copy()
    updated_last_prices.rename(columns={"price": "last_price"}, inplace=True)
    updated_last_prices["last_seen_date"] = now_utc()

    updated_last_prices.to_csv(LAST_PRICES_PATH, index=False)

# =====================
# Example usage
# =====================
if __name__ == "__main__":
    # This is just a placeholder example
    # In reality, you pass the DataFrame from your fetch script
    snapshot = pd.DataFrame([
        {"player_id": 1, "price": 75},
        {"player_id": 2, "price": 62},
    ])

    record_price_changes(snapshot)    if merged.empty:
        print("ℹ️ No price changes today")
        return

    out = merged[[
        "player_id",
        "web_name_curr",
        "actual_change"
    ]].rename(columns={"web_name_curr": "web_name"})

    out.insert(0, "date", date.today())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    print(f"💰 Price changes recorded: {len(out)}")

if __name__ == "__main__":
    main()
