from pathlib import Path
import sys

import pandas as pd

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient
from agu_quant.features import add_ma_trend_labels


def main() -> None:
    end = pd.Timestamp.today().strftime("%Y-%m-%d")
    start = (pd.Timestamp.today() - pd.Timedelta(days=200)).strftime("%Y-%m-%d")

    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True, verbose=True)
    stocks = client.stock_list().head(3)
    if stocks is None or stocks.empty:
        print("Stock list is empty.")
        return

    frames = []
    for _, row in stocks.iterrows():
        symbol = row["symbol"]
        bars = client.daily_bars(symbol, start=start, end=end, adjust="qfq")
        if bars is None or bars.empty:
            continue
        frames.append(bars)

    if not frames:
        print("No bars fetched.")
        return

    df = pd.concat(frames, ignore_index=True)
    df = add_ma_trend_labels(df, windows=(5, 10, 20, 60))

    cols = [
        "date",
        "symbol",
        "close",
        "ma_5",
        "ma_10",
        "ma_20",
        "ma_60",
        "ma_stack_bull",
        "ma_stack_bear",
        "price_above_ma",
        "price_below_ma",
        "ma_slope_up",
        "ma_slope_down",
        "trend_state",
    ]
    keep = [c for c in cols if c in df.columns]
    print("Latest rows:")
    print(df[keep].tail(15))

    print("\nTrend state counts:")
    print(df["trend_state"].value_counts())


if __name__ == "__main__":
    main()
