from pathlib import Path
import pandas as pd
from datetime import date
import requests
import os

# =====================
# Paths
# =====================
PRED_PATH = Path("data/predictions.csv")
SUMMARY_PATH = Path("data/summary.csv")

# =====================
# Tunables
# =====================
TARGET_MIN = 8
TARGET_MAX = 12
HARD_MAX = 20

# =====================
# Telegram
# =====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram not configured")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Telegram error: {e}")

def main():
    if not PRED_PATH.exists():
        print("⚠️ predictions.csv missing")
        return

    df = pd.read_csv(PRED_PATH)

    if df.empty:
        print("ℹ️ No predictions available")
        return

    today = date.today()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # ---------------------
    # Tonight only
    # ---------------------
    df = df[df["date"] == today].copy()

    if df.empty:
        print("ℹ️ No predictions for tonight")
        return

    # ---------------------
    # Rank by confidence / pressure
    # ---------------------
    score_col = "pressure" if "pressure" in df.columns else None
    if not score_col:
        raise RuntimeError("Prediction score column missing")

    df = (
        df.sort_values(score_col, ascending=False)
          .drop_duplicates(subset=["player_id"], keep="first")
    )

    # ---------------------
    # Soft cap logic
    # ---------------------
    if len(df) > TARGET_MAX:
        cutoff = df.iloc[TARGET_MAX - 1][score_col]
        df = df[df[score_col] >= cutoff]

    df = df.head(HARD_MAX)

    if df.empty:
        print("ℹ️ All signals filtered out")
        return

    # ---------------------
    # Persist summary
    # ---------------------
    out = df[[
        "player_id",
        "web_name",
        "direction",
        score_col
    ]].copy()

    out.insert(0, "date", today)

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(SUMMARY_PATH, index=False)

    # ---------------------
    # Message
    # ---------------------
    lines = [
        "📊 *FPL Daily Summary*",
        f"📅 {today.isoformat()}",
        "",
        f"🚨 *Signals*: {len(out)}",
        ""
    ]

    for _, r in out.iterrows():
        arrow = "⬆️" if r["direction"] == "rise" else "⬇️"
        lines.append(
            f"{arrow} *{r['web_name']}* — {r[score_col]:.2f}"
        )

    msg = "\n".join(lines)

    print(f"📊 Daily summary generated | {len(out)} players")
    send_telegram(msg)

if __name__ == "__main__":
    main()
