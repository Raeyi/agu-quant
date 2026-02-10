# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from agu_quant.features.limitup import add_limit_up_flags


def add_pattern_flags(
    df: pd.DataFrame,
    breakout_window: int = 20,
    volume_window: int = 20,
    volume_ratio: float = 1.5,
    shrink_ratio: float = 0.7,
    turnover_threshold: float = 0.15,
    limit_up_thres: float = 0.095,
    limit_down_thres: float = -0.095,
    eps: float = 1e-6,
) -> pd.DataFrame:
    """
    关键形态识别：
    - 放量突破
    - 换手板
    - 一字板
    - 缩量板

    依赖字段：
    date, open, high, low, close, volume, pct_chg
    可选字段：
    symbol, turnover

    输出字段：
    breakout_volume, turnover_board, one_word_board, shrink_volume_board
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["_date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["_date"])
    if out.empty:
        return pd.DataFrame()

    need_cols = ["open", "high", "low", "close", "volume", "pct_chg"]
    for col in need_cols:
        if col not in out.columns:
            return pd.DataFrame()

    out = add_limit_up_flags(out, limit_up_thres, limit_down_thres)
    group_cols = ["symbol"] if "symbol" in out.columns else []
    out = out.sort_values(group_cols + ["_date"])

    def _compute(group: pd.DataFrame) -> pd.DataFrame:
        close = group["close"].astype(float)
        volume = group["volume"].astype(float)
        pct = group["pct_chg"].astype(float)

        prev_max = close.rolling(window=breakout_window, min_periods=1).max().shift(1)
        vol_ma = volume.rolling(window=volume_window, min_periods=1).mean()

        breakout = (close >= prev_max) & (volume >= vol_ma * volume_ratio) & (pct > 0)
        breakout = breakout.fillna(False)

        open_p = group["open"].astype(float)
        high_p = group["high"].astype(float)
        low_p = group["low"].astype(float)

        one_word = (
            (group["limit_up"] == 1)
            & (abs(open_p - high_p) <= eps)
            & (abs(high_p - low_p) <= eps)
            & (abs(close - high_p) <= eps)
        )

        if "turnover" in group.columns:
            turnover = group["turnover"].astype(float)
            turnover_board = (group["limit_up"] == 1) & (turnover >= turnover_threshold)
        else:
            turnover_board = pd.Series(False, index=group.index)

        shrink = (group["limit_up"] == 1) & (volume <= vol_ma * shrink_ratio)
        shrink = shrink.fillna(False)

        group["breakout_volume"] = breakout.astype(int)
        group["turnover_board"] = turnover_board.astype(int)
        group["one_word_board"] = one_word.astype(int)
        group["shrink_volume_board"] = shrink.astype(int)
        return group

    if group_cols:
        out = out.groupby(group_cols, group_keys=False).apply(_compute)
    else:
        out = _compute(out)

    out = out.drop(columns=["_date"])
    return out
