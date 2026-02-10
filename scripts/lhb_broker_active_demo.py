from pathlib import Path
import sys

import pandas as pd

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient
from agu_quant.features import (
    compute_lhb_broker_daily,
    compute_lhb_broker_heat_panel,
)


def main() -> None:
    end = pd.Timestamp.today().strftime("%Y%m%d")
    start = (pd.Timestamp.today() - pd.Timedelta(days=60)).strftime("%Y%m%d")

    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True, verbose=True)
    df = client.lhb_broker_active_em(start_date=start, end_date=end)
    if df is None or df.empty:
        print("LHB broker active result is empty.")
        return

    daily = compute_lhb_broker_daily(df)
    panel = compute_lhb_broker_heat_panel(df, window=20)

    print("Daily tail:")
    print(daily.tail(10))
    print("\nHeat panel (top 20 by net):")
    print(panel.sort_values("net", ascending=False).head(20))


if __name__ == "__main__":
    main()
