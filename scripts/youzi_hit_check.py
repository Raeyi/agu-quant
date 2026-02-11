from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient
from agu_quant.youzi import load_youzi_whitelist, build_youzi_hits


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True)
    whitelist = load_youzi_whitelist(Path("data/youzi_whitelist.csv"))
    if not whitelist:
        print("empty whitelist")
        return

    end_date = date.today()
    start_date = end_date - timedelta(days=45)
    df = client.lhb_broker_active_em(
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
    )
    if df is None or df.empty:
        print("no broker active data")
        return

    # Use latest available date in dataset
    latest_date = (
        pd.to_datetime(df["date"], errors="coerce")
        .dropna()
        .max()
        .strftime("%Y-%m-%d")
    )
    hits = build_youzi_hits(df, whitelist, latest_date)
    if not hits:
        print(f"no youzi hits on {latest_date}")
        return

    rows = []
    for sym, hit in hits.items():
        rows.append({"symbol": sym, "youzi_hit": hit.hit, "youzi_brokers": ";".join(hit.brokers)})
    out = pd.DataFrame(rows).sort_values(["youzi_hit", "symbol"], ascending=[False, True])
    out_path = Path("data/reports/youzi_hit_check.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    pd.set_option("display.max_columns", None)
    print(out.head(20))
    print(f"written {out_path}")


if __name__ == "__main__":
    main()
