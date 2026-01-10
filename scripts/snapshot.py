from pathlib import Path
import requests
import pandas as pd
from datetime import datetime
import sys

# =====================
# Constants
# =====================
FPL_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

DATA_DIR = Path("data")
SNAPSHOT_DIR = DATA_DIR / "snapshots"
LATEST_PATH = DATA_DIR / "latest.csv"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# =====================
# Main
# =====================
def main():
    try:
        r = requests.get(FPL_URL, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch FPL data: {e}")
        sys.exit(1)

    data = r.json()

    teams = {t["id"]: t["name"] for t in data["teams"]}

    rows = []
    snapshot_time = datetime.utcnow()

    for p in data["elements"]:
        # ✅ ACTIVE PLAYERS ONLY
        if p["status"] != "a":
            continue

        rows.append({
            "player_id": p["id"],
            "web_name": p["web_name"],
            "first_name": p["first_name"],
            "second_name": p["second_name"],
            "team": teams.get(p["team"], ""),
            "team_id": p["team"],
            "position": p["element_type"],

            # Price
            "price": p["now_cost"] / 10,
            "now_cost": p["now_cost"],

            # Ownership & transfers
            "ownership": float(p["selected_by_percent"]),
            "transfers_in_event": p["transfers_in_event"],
            "transfers_out_event": p["transfers_out_event"],

            # Metadata
            "status": p["status"],
            "snapshot_time": snapshot_time.isoformat(),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        print("❌ Snapshot produced 0 active players")
        sys.exit(1)

    # ---------------------
    # Write files
    # ---------------------
    ts = snapshot_time.strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_path = SNAPSHOT_DIR / f"snapshot_{ts}.csv"

    df.to_csv(snapshot_path, index=False)
    df.to_csv(LATEST_PATH, index=False)

    if not LATEST_PATH.exists():
        raise RuntimeError("latest.csv was not created")

    print(f"📸 Snapshot saved: {snapshot_path}")
    print(f"🆕 latest.csv updated ({len(df)} active players)")

if __name__ == "__main__":
    main()
