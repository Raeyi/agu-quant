from pathlib import Path
import sys

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient
from agu_quant.features import compute_sentiment_panel


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True, verbose=True)
    symbols = ["000001.SZ", "000002.SZ", "600000.SH", "600519.SH"]
    bars_by_symbol = {}

    for symbol in symbols:
        try:
            bars = client.daily_bars(
                symbol,
                start="2024-01-01",
                end="2024-06-30",
                adjust="qfq",
                timeout=15,
            )
            bars_by_symbol[symbol] = bars
        except Exception as exc:
            print(f"{symbol} 拉取失败: {exc}")

    panel = compute_sentiment_panel(bars_by_symbol)
    if panel is None or panel.empty:
        print("面板为空，可能是数据未获取到。")
        return

    print(panel.tail(5))


if __name__ == "__main__":
    main()
