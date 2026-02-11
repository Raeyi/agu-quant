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
from agu_quant.features.flow import compute_lhb_broker_heat_panel


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True)
    end_date = date.today()
    start_date = end_date - timedelta(days=45)
    start = start_date.strftime("%Y%m%d")
    end = end_date.strftime("%Y%m%d")

    df = client.lhb_broker_active_em(start_date=start, end_date=end)
    if df is None or df.empty:
        print("no broker active data")
        return

    heat = compute_lhb_broker_heat_panel(df, window=20)
    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "youzi_active_brokers.csv"
    heat.to_csv(out_path, index=False)
    print(f"written {out_path}")


if __name__ == "__main__":
    main()
