from pathlib import Path
import pandas as pd
from datetime import datetime

# =====================
# Paths
# =====================
PRED_PATH = Path("data/predictions.csv")
CHANGES_PATH = Path("data/price_changes.csv")
EVAL_PATH = Path("data/evaluation.csv")

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
    preds = safe_read_csv(PRED_PATH)
    changes = safe_read_csv(CHANGES_PATH)

    if preds.empty or changes.empty:
        print("ℹ️ Nothing to evaluate yet")
        return

    preds["date"] = pd.to_datetime(preds["date"])
    changes["date"] = pd.to_datetime(changes["date"])

    preds = preds.sort_values("date")
    changes = changes.sort_values("date")

    # Already evaluated predictions
    evaluated = safe_read_csv(EVAL_PATH)
    evaluated_keys = set()

    if not evaluated.empty:
        evaluated_keys = set(
            zip(evaluated["player_id"], pd.to_datetime(evaluated["prediction_date"]))
        )

    rows = []

    for _, p in preds.iterrows():
        key = (p["player_id"], p["date"])
        if key in evaluated_keys:
            continue

        future_changes = changes[
            (changes["player_id"] == p["player_id"]) &
            (changes["date"] > p["date"])
        ]

        if future_changes.empty:
            continue

        first_change = future_changes.iloc[0]

        correct = first_change["change"] == p["direction"]

        rows.append({
            "player_id": p["player_id"],
            "prediction_date": p["date"].strftime("%Y-%m-%d"),
            "predicted": p["direction"],
            "actual": first_change["change"],
            "correct": correct,
            "resolved_date": first_change["date"].strftime("%Y-%m-%d"),
            "score": p.get("score", None),
        })

    if not rows:
        print("ℹ️ No new resolved predictions")
        return

    out = pd.DataFrame(rows)

    if EVAL_PATH.exists():
        out = pd.concat([evaluated, out], ignore_index=True)

    EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(EVAL_PATH, index=False)

    acc = out["correct"].mean() * 100
    print(f"📊 Evaluated {len(rows)} predictions | Accuracy: {acc:.1f}%")

if __name__ == "__main__":
    main()
