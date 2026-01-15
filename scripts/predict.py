from pathlib import Path
import pandas as pd
from datetime import date, timedelta
import numpy as np

# =====================
# Paths
# =====================
LATEST_PATH = Path("data/latest.csv")
HISTORY_PATH = Path("data/history.csv")
SUMMARY_PATH = Path("data/summary.csv")
OUT_PATH = Path("data/predictions.csv")

# =====================
# Tunables
# =====================
MAX_SIGNALS = 20
DECAY = 0.6
THRESH_STD = 0.75
EXCEPTION_MULT = 1.8

def main():
    if not LATEST_PATH.exists():
        raise RuntimeError("latest.csv missing")

    today = date.today()

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

    df["ownership"] = df["ownership"].clip(lower=0.1)

    # ---------------------
    # Base pressure (today)
    # ---------------------
    df["pressure"] = (
        df["transfers_in_event"] - df["transfers_out_event"]
    ) / df["ownership"]

    df_today = df[["player_id", "web_name", "pressure"]].copy()
    df_today["date"] = today

    # ---------------------
    # Load history
    # ---------------------
    if HISTORY_PATH.exists():
        hist = pd.read_csv(HISTORY_PATH, parse_dates=["date"])
        hist["date"] = hist["date"].dt.date
    else:
        hist = pd.DataFrame(columns=["date", "player_id", "pressure"])

    # Append today to history
    hist = pd.concat([
        hist,
        df_today[["date", "player_id", "pressure"]]
    ], ignore_index=True)

    hist = hist.drop_duplicates(
        subset=["date", "player_id"], keep="last"
    )

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    hist.to_csv(HISTORY_PATH, index=False)

    # ---------------------
    # Build rolling view
    # ---------------------
    def get_pressure(day_offset):
        d = today - timedelta(days=day_offset)
        s = hist[hist["date"] == d][["player_id", "pressure"]]
        return s.set_index("player_id")["pressure"]

    p0 = df_today.set_index("player_id")["pressure"]
    p1 = get_pressure(1)
    p2 = get_pressure(2)

    roll = pd.DataFrame({
        "pressure_today": p0,
        "pressure_yesterday": p1,
        "pressure_2d": p2,
    }).fillna(0)

    # ---------------------
    # A + B: delta + decay
    # ---------------------
    roll["delta_pressure"] = (
        roll["pressure_today"] - roll["pressure_yesterday"]
    )

    roll["decayed_pressure"] = (
        roll["pressure_today"]
        + DECAY * roll["pressure_yesterday"]
        + (DECAY ** 2) * roll["pressure_2d"]
    )

    # ---------------------
    # Final signal score
    # ---------------------
    roll["signal_score"] = (
        0.6 * roll["delta_pressure"]
        + 0.4 * roll["decayed_pressure"]
    )

    roll = roll.reset_index()

    merged = roll.merge(
        df_today[["player_id", "web_name"]],
        on="player_id",
        how="left"
    )

    # ---------------------
    # C: dynamic threshold
    # ---------------------
    mean = merged["signal_score"].mean()
    std = merged["signal_score"].std(ddof=0)

    threshold = mean + THRESH_STD * std

    signals = merged[merged["signal_score"] >= threshold].copy()

    # ---------------------
    # D: soft exclude recent
    # ---------------------
    if SUMMARY_PATH.exists():
        recent = pd.read_csv(SUMMARY_PATH)
        recent["date"] = pd.to_datetime(recent["date"]).dt.date
        recent = recent[
            recent["date"].isin([today - timedelta(days=1),
                                  today - timedelta(days=2)])
        ]
        recent_ids = set(recent["player_id"])
    else:
        recent_ids = set()

    signals["recent"] = signals["player_id"].isin(recent_ids)

    signals = signals[
        (~signals["recent"]) |
        (signals["signal_score"] >= EXCEPTION_MULT * threshold)
    ]

    # ---------------------
    # Direction
    # ---------------------
    signals["direction"] = np.where(
        signals["delta_pressure"] > 0,
        "rise",
        "fall"
    )

    # ---------------------
    # Hard cap (absolute)
    # ---------------------
    signals = (
        signals.sort_values("signal_score", ascending=False)
               .head(MAX_SIGNALS)
    )

    # ---------------------
    # Output
    # ---------------------
    out = signals[[
        "player_id",
        "web_name",
        "direction",
        "signal_score"
    ]].copy()

    out.insert(0, "date", today)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    print(f"🔮 Predictions written: {len(out)} players")

if __name__ == "__main__":
    main()
