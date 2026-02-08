from __future__ import annotations

import pandas as pd


def add_limit_up_flags(
    bars: pd.DataFrame,
    limit_up_thres: float = 0.095,
    limit_down_thres: float = -0.095,
) -> pd.DataFrame:
    """
    基于日线的涨跌停/炸板近似标记。
    依赖字段: date, close, high, low, pct_chg
    """
    if bars is None or bars.empty:
        return pd.DataFrame()

    df = bars.sort_values("date").copy()
    df["prev_close"] = df["close"].shift(1)
    df["high_pct"] = (df["high"] / df["prev_close"] - 1).fillna(0.0)
    df["low_pct"] = (df["low"] / df["prev_close"] - 1).fillna(0.0)

    df["limit_up"] = (df["pct_chg"] >= limit_up_thres).astype(int)
    df["limit_down"] = (df["pct_chg"] <= limit_down_thres).astype(int)
    # 炸板：盘中触及涨停，但收盘未涨停
    df["broken_limit_up"] = (
        (df["high_pct"] >= limit_up_thres) & (df["pct_chg"] < limit_up_thres)
    ).astype(int)

    return df


def consecutive_limit_up(df: pd.DataFrame) -> pd.Series:
    """
    计算连续涨停天数（基于 limit_up 列）。
    """
    if df is None or df.empty or "limit_up" not in df.columns:
        return pd.Series(dtype=int)

    counts = []
    streak = 0
    for v in df["limit_up"].fillna(0).astype(int):
        if v == 1:
            streak += 1
        else:
            streak = 0
        counts.append(streak)
    return pd.Series(counts, index=df.index)
