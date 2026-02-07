from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient
from agu_quant.reporting import build_candidate_pool
from agu_quant.signals.scoring_config import ScoringConfig


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True)

    symbols = [
        "000001.SZ",
        "600000.SH",
        "000333.SZ",
        "600519.SH",
    ]

    config_path = Path("docs/scoring_config.sample.json")
    config = ScoringConfig.from_json(config_path)

    df = build_candidate_pool(
        symbols=symbols,
        start="2024-01-01",
        end="2024-06-30",
        client=client,
        config=config,
    )

    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "candidate_pool_demo.csv"
    df.to_csv(out_path, index=False)

    pd.set_option("display.max_columns", None)
    print(df)
    print(f"已输出: {out_path}")


if __name__ == "__main__":
    main()
