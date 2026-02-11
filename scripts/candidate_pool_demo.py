from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datetime import date, timedelta

from agu_quant.data import AkShareClient, normalize_symbol
from agu_quant.youzi import load_youzi_whitelist
from agu_quant.reporting import build_candidate_pool
from agu_quant.signals.scoring_config import ScoringConfig


def _load_industry_map() -> dict[str, str]:
    candidates = [
        Path("data/industry_map.csv"),
        Path("data/ths_industry.csv"),
        Path("data/industry.csv"),
        Path("data/ths_industry.json"),
        Path("data/industry.json"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == ".json":
            raw = path.read_text(encoding="utf-8-sig").strip()
            if not raw:
                continue
            data = pd.read_json(path, typ="series").to_dict() if raw.startswith("{") else pd.read_json(path).to_dict(orient="records")
            mapping: dict[str, str] = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if k and v:
                        mapping[normalize_symbol(str(k))] = str(v)
            else:
                for row in data:
                    sym = row.get("symbol") or row.get("code") or row.get("证券代码")
                    ind = row.get("industry") or row.get("ths_industry") or row.get("同花顺行业") or row.get("行业")
                    if sym and ind:
                        mapping[normalize_symbol(str(sym))] = str(ind)
            if mapping:
                print(f"[industry_map] loaded {len(mapping)} from {path}")
                return mapping
            continue

        df = pd.read_csv(path)
        if df.empty:
            continue
        symbol_col = None
        for c in ["symbol", "code", "证券代码", "股票代码"]:
            if c in df.columns:
                symbol_col = c
                break
        industry_col = None
        for c in ["industry", "ths_industry", "同花顺行业", "行业"]:
            if c in df.columns:
                industry_col = c
                break
        if symbol_col and industry_col:
            mapping = {}
            for _, row in df[[symbol_col, industry_col]].dropna().iterrows():
                mapping[normalize_symbol(str(row[symbol_col]))] = str(row[industry_col])
            if mapping:
                print(f"[industry_map] loaded {len(mapping)} from {path}")
                return mapping
    print("[industry_map] no mapping file found under data/")
    return {}


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

    industry_map = _load_industry_map()
    whitelist = load_youzi_whitelist(Path("data/youzi_whitelist.csv"))
    broker_active_df = None
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=45)
        broker_active_df = client.lhb_broker_active_em(
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
    except Exception:
        broker_active_df = None

    df = build_candidate_pool(
        symbols=symbols,
        start="2024-01-01",
        end="2024-06-30",
        client=client,
        config=config,
        industry_map=industry_map,
        broker_active_df=broker_active_df,
        youzi_whitelist=list(whitelist),
    )
    ordered_cols = [
        "symbol",
        "date",
        "close",
        "pct_chg",
        "turnover",
        "amount",
        "industry",
        "industry_consecutive",
        "youzi_hit",
        "youzi_brokers",
        "limit_up",
        "broken_limit_up",
        "consecutive",
        "breakout_volume",
        "turnover_board",
        "one_word_board",
        "shrink_volume_board",
        "turnover_z",
        "turnover_norm",
        "turnover_pct_rank",
        "score",
        "suggested_position",
        "reason",
        "ret_3d",
        "ret_10d",
        "ret_20d",
        "avg_amount_5d",
        "vol_5d",
        "drawdown_10d",
    ]
    if not df.empty:
        existing = [c for c in ordered_cols if c in df.columns]
        remaining = [c for c in df.columns if c not in existing]
        df = df[existing + remaining]

    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "candidate_pool_demo.csv"
    df.to_csv(out_path, index=False)

    pd.set_option("display.max_columns", None)
    print(df)
    print(f"已输出: {out_path}")


if __name__ == "__main__":
    main()
