from pathlib import Path
import pandas as pd
from datetime import date

# =====================
# Paths
# =====================
LATEST_PATH = Path("data/latest.csv")
OUT_PATH = Path("data/predictions.csv")

# =====================
# Tunables (LiveFPL-ish)
# =====================
TOP_RISES = 10
TOP_FALLS = 10

def main():
    if not LATEST_PATH.exists():
        raise RuntimeError("latest.csv missing")

    df = pd.read_csv(LATEST_PATH)

    required = {
        "player_id",
        "web_name",
        "transfers_in_event",
        "transfers_out_event",
        "ownership",
        "status",
    }
    if not required.issubset(df.columns):
        raise RuntimeError("latest.csv missing required columns")

    # Active players only
    df = df[df["status"].isin(["a", "d"])].copy()

    # Avoid division by zero
    df["ownership"] = df["ownership"].clip(lower=0.1)

    # Pressure score
    df["pressure"] = (
        df["transfers_in_event"] - df["transfers_out_event"]
    ) / df["ownership"]

    # Rank
    rises = (
        df.sort_values("pressure", ascending=False)
          .head(TOP_RISES)
          .assign(direction="rise")
    )

    falls = (
        df.sort_values("pressure", ascending=True)
          .head(TOP_FALLS)
          .assign(direction="fall")
    )

    out = pd.concat([rises, falls], ignore_index=True)

    out = out[[
        "player_id",
        "web_name",
        "direction",
        "pressure",
    ]].copy()

    out.insert(0, "date", date.today())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    print(f"🔮 Predictions written: {len(out)} players")

if __name__ == "__main__":
    main()
