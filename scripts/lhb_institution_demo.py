from pathlib import Path
import sys

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient
from agu_quant.features import compute_lhb_institution_daily


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True, verbose=True)
    df = client.lhb_institution_detail_sina()
    daily = compute_lhb_institution_daily(df)
    if daily is None or daily.empty:
        print("龙虎榜机构净买卖结果为空。")
        return
    print(daily.tail(10))


if __name__ == "__main__":
    main()
