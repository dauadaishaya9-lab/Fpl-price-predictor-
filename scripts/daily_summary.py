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
    # Today only
    # ---------------------
    df = df[df["date"] == today].copy()

    if df.empty:
        print("ℹ️ No predictions for today")
        return

    # ---------------------
    # Validate score column
    # ---------------------
    if "signal_score" not in df.columns:
        raise RuntimeError("signal_score column missing")

    # ---------------------
    # Final ranking (trust upstream)
    # ---------------------
    df = (
        df.sort_values("signal_score", ascending=False)
          .drop_duplicates(subset=["player_id"], keep="first")
          .head(HARD_MAX)
    )

    if df.empty:
        print("ℹ️ All signals filtered out")
        return

    # ---------------------
    # Persist summary (APPEND)
    # ---------------------
    out = df[[
        "player_id",
        "web_name",
        "direction",
        "signal_score"
    ]].copy()

    out.insert(0, "date", today)

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if SUMMARY_PATH.exists():
        existing = pd.read_csv(SUMMARY_PATH)
        existing["date"] = pd.to_datetime(existing["date"]).dt.date
        out = pd.concat([existing, out], ignore_index=True)

    out.to_csv(SUMMARY_PATH, index=False)

    # ---------------------
    # Message
    # ---------------------
    lines = [
        "📊 *FPL Daily Summary*",
        f"📅 {today.isoformat()}",
        "",
        f"🚨 *Signals*: {len(df)}",
        ""
    ]

    for _, r in df.iterrows():
        arrow = "⬆️" if r["direction"] == "rise" else "⬇️"
        lines.append(
            f"{arrow} *{r['web_name']}* — {r['signal_score']:.2f}"
        )

    msg = "\n".join(lines)

    print(f"📊 Daily summary generated | {len(df)} players")
    send_telegram(msg)

if __name__ == "__main__":
    main()
