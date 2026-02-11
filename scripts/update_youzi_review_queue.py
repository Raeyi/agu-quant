from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.youzi import load_youzi_whitelist


def main() -> None:
    whitelist = load_youzi_whitelist(Path("data/youzi_whitelist.csv"))
    if not whitelist:
        print("empty whitelist")
        return

    active_path = Path("data/youzi_active_brokers.csv")
    if not active_path.exists():
        print("missing data/youzi_active_brokers.csv, run update_youzi_active_brokers.py first")
        return

    active = pd.read_csv(active_path)
    if active.empty or "broker" not in active.columns:
        print("active broker data is empty")
        return

    active["broker"] = active["broker"].astype(str).str.strip()
    active["in_whitelist"] = active["broker"].isin(whitelist)
    # candidates = active but not yet in whitelist
    candidates = active[~active["in_whitelist"]].copy()
    candidates = candidates.sort_values(["net", "active_days", "buy_ratio"], ascending=[False, False, False])

    out_path = Path("data/youzi_review_queue.csv")
    candidates.to_csv(out_path, index=False)
    print(f"written {out_path}")


if __name__ == "__main__":
    main()
