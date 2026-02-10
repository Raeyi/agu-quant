from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd


def add_ma_trend_labels(
    df: pd.DataFrame,
    windows: Sequence[int] = (5, 10, 20, 60),
    require_price_confirm: bool = True,
    require_slope_confirm: bool = True,
    eps: float = 1e-6,
) -> pd.DataFrame:
    """
    均线结构与趋势状态标签。

    依赖字段：
    date, close
    可选字段：
    symbol

    输出字段（示例）：
    ma_5, ma_10, ma_20, ma_60,
    ma_5_slope, ma_10_slope, ma_20_slope, ma_60_slope,
    ma_stack_bull, ma_stack_bear,
    price_above_ma, price_below_ma,
    ma_slope_up, ma_slope_down,
    trend_state
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if "date" not in out.columns or "close" not in out.columns:
        return pd.DataFrame()

    out["_date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["_date"])
    if out.empty:
        return pd.DataFrame()

    group_cols = ["symbol"] if "symbol" in out.columns else []
    out = out.sort_values(group_cols + ["_date"])

    win_list = [int(w) for w in windows if int(w) > 0]
    if not win_list:
        return pd.DataFrame()

    def _compute(group: pd.DataFrame) -> pd.DataFrame:
        close = group["close"].astype(float)
        for w in win_list:
            ma_col = f"ma_{w}"
            slope_col = f"{ma_col}_slope"
            group[ma_col] = close.rolling(window=w, min_periods=1).mean()
            group[slope_col] = group[ma_col] - group[ma_col].shift(1)

        short_w, mid_w, long_w = _pick_windows(win_list)
        ma_s = group[f"ma_{short_w}"]
        ma_m = group[f"ma_{mid_w}"]
        ma_l = group[f"ma_{long_w}"]

        bull = (ma_s > ma_m + eps) & (ma_m > ma_l + eps)
        bear = (ma_s < ma_m - eps) & (ma_m < ma_l - eps)

        group["ma_stack_bull"] = bull.astype(int)
        group["ma_stack_bear"] = bear.astype(int)

        close = group["close"].astype(float)
        price_above = (close > ma_m + eps) & (close > ma_l + eps)
        price_below = (close < ma_m - eps) & (close < ma_l - eps)
        group["price_above_ma"] = price_above.astype(int)
        group["price_below_ma"] = price_below.astype(int)

        slope_short = group[f"ma_{short_w}_slope"]
        slope_mid = group[f"ma_{mid_w}_slope"]
        slope_long = group[f"ma_{long_w}_slope"]
        slope_up = (slope_short > 0) & (slope_mid > 0) & (slope_long > 0)
        slope_down = (slope_short < 0) & (slope_mid < 0) & (slope_long < 0)
        group["ma_slope_up"] = slope_up.astype(int)
        group["ma_slope_down"] = slope_down.astype(int)

        bull_ok = bull.copy()
        bear_ok = bear.copy()
        if require_price_confirm:
            bull_ok = bull_ok & price_above
            bear_ok = bear_ok & price_below
        if require_slope_confirm:
            bull_ok = bull_ok & slope_up
            bear_ok = bear_ok & slope_down

        trend_state = pd.Series("side", index=group.index, dtype="object")
        trend_state = trend_state.where(~bull_ok, "up")
        trend_state = trend_state.where(~bear_ok, "down")
        group["trend_state"] = trend_state
        return group

    if group_cols:
        out = out.groupby(group_cols, group_keys=False).apply(_compute)
    else:
        out = _compute(out)

    out = out.drop(columns=["_date"])
    return out


def _pick_windows(windows: Iterable[int]) -> tuple[int, int, int]:
    win = sorted(set(int(w) for w in windows if int(w) > 0))
    if len(win) >= 3:
        return win[0], win[1], win[-1]
    if len(win) == 2:
        return win[0], win[1], win[1]
    return win[0], win[0], win[0]
