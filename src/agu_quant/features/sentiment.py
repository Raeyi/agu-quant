from __future__ import annotations

from typing import Dict

import pandas as pd

from agu_quant.features.limitup import add_limit_up_flags, consecutive_limit_up


def compute_sentiment_daily(
    bars_by_symbol: Dict[str, pd.DataFrame],
    limit_up_thres: float = 0.095,
    limit_down_thres: float = -0.095,
) -> pd.DataFrame:
    """
    计算情绪指标（日频）。
    输出字段:
    date, total, limit_up, limit_down, broken, limit_up_ratio, max_consecutive
    """
    frames = []
    for symbol, bars in bars_by_symbol.items():
        if bars is None or bars.empty:
            continue
        df = add_limit_up_flags(bars, limit_up_thres, limit_down_thres)
        df["consecutive"] = consecutive_limit_up(df)
        df["symbol"] = symbol
        frames.append(df[["date", "symbol", "limit_up", "limit_down", "broken_limit_up", "consecutive"]])

    if not frames:
        return pd.DataFrame()

    all_df = pd.concat(frames, ignore_index=True)
    g = all_df.groupby("date")
    sentiment = g.agg(
        total=("symbol", "count"),
        limit_up=("limit_up", "sum"),
        limit_down=("limit_down", "sum"),
        broken=("broken_limit_up", "sum"),
        max_consecutive=("consecutive", "max"),
    ).reset_index()
    sentiment["limit_up_ratio"] = sentiment["limit_up"] / sentiment["total"]
    return sentiment
