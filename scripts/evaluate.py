from pathlib import Path
import pandas as pd
from datetime import timedelta

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

    preds["date"] = pd.to_datetime(preds["date"]).dt.date
    changes["date"] = pd.to_datetime(changes["date"]).dt.date

    # Load existing evaluations
    evaluated = safe_read_csv(EVAL_PATH)
    evaluated_keys = set()

    if not evaluated.empty:
        evaluated["prediction_date"] = pd.to_datetime(
            evaluated["prediction_date"]
        ).dt.date
        evaluated_keys = set(
            zip(evaluated["player_id"], evaluated["prediction_date"])
        )

    rows = []

    for _, p in preds.iterrows():
        key = (p["player_id"], p["date"])
        if key in evaluated_keys:
            continue

        d0 = p["date"]
        d1 = d0 + timedelta(days=1)

        window = changes[
            (changes["player_id"] == p["player_id"]) &
            (changes["date"].isin([d0, d1]))
        ]

        if window.empty:
            # Miss: no movement in D or D+1
            rows.append({
                "player_id": p["player_id"],
                "prediction_date": d0.isoformat(),
                "predicted": p["direction"],
                "actual": "none",
                "correct": False,
                "resolved_date": None,
            })
            continue

        first = window.sort_values("date").iloc[0]
        actual = first["change"]
        correct = actual == p["direction"]

        rows.append({
            "player_id": p["player_id"],
            "prediction_date": d0.isoformat(),
            "predicted": p["direction"],
            "actual": actual,
            "correct": correct,
            "resolved_date": first["date"].isoformat(),
        })

    if not rows:
        print("ℹ️ No new resolved predictions")
        return

    out = pd.DataFrame(rows)

    if not evaluated.empty:
        out = pd.concat([evaluated, out], ignore_index=True)

    EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(EVAL_PATH, index=False)

    acc = out["correct"].mean() * 100
    print(f"📊 Evaluated {len(rows)} predictions | Accuracy: {acc:.1f}%")

if __name__ == "__main__":
    main()
