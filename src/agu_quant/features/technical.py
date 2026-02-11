# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


def _first_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _rolling_pct_rank(series: pd.Series, window: int) -> pd.Series:
    def _pct_rank(x: pd.Series) -> float:
        return x.rank(pct=True).iloc[-1]

    return series.rolling(window=window, min_periods=1).apply(_pct_rank, raw=False)


def add_turnover_standardized(
    df: pd.DataFrame, window: int = 20
) -> pd.DataFrame:
    """
    换手率标准化（滚动统计）。
    依赖字段：date, turnover
    可选字段：symbol
    输出字段：
    turnover_z, turnover_norm, turnover_pct_rank
    """
    if df is None or df.empty or "turnover" not in df.columns:
        return pd.DataFrame()

    out = df.copy()
    out["_date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["_date"])
    if out.empty:
        return pd.DataFrame()

    group_cols = ["symbol"] if "symbol" in out.columns else []
    out = out.sort_values(group_cols + ["_date"])

    def _compute(group: pd.DataFrame) -> pd.DataFrame:
        turnover = group["turnover"].astype(float)
        roll = turnover.rolling(window=window, min_periods=1)
        mean = roll.mean()
        std = roll.std(ddof=0).replace(0, pd.NA)
        min_v = roll.min()
        max_v = roll.max()
        denom = (max_v - min_v).replace(0, pd.NA)

        turnover_z = (turnover - mean) / std
        turnover_norm = (turnover - min_v) / denom
        group["turnover_z"] = pd.to_numeric(turnover_z, errors="coerce").fillna(0.0)
        group["turnover_norm"] = pd.to_numeric(turnover_norm, errors="coerce").fillna(0.0)
        group["turnover_pct_rank"] = _rolling_pct_rank(turnover, window=window)
        return group

    if group_cols:
        out = out.groupby(group_cols, group_keys=False).apply(
            _compute, include_groups=False
        )
    else:
        out = _compute(out)

    out = out.drop(columns=["_date"])
    return out


def add_orderbook_strength(
    df: pd.DataFrame, window: int = 20
) -> pd.DataFrame:
    """
    计算封单强度（买一/卖一）及其标准化分数。
    支持字段：
    buy1_volume/sell1_volume 或 bid1_volume/ask1_volume 或 买一量/卖一量
    可选字段：symbol, date
    输出字段：
    orderbook_strength, orderbook_imbalance,
    orderbook_z, orderbook_norm
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    buy_col = _first_column(
        out, ["buy1_volume", "bid1_volume", "buy1_vol", "买一量", "买一委托量"]
    )
    sell_col = _first_column(
        out, ["sell1_volume", "ask1_volume", "sell1_vol", "卖一量", "卖一委托量"]
    )

    if buy_col is None or sell_col is None:
        return pd.DataFrame()

    buy = pd.to_numeric(out[buy_col], errors="coerce").fillna(0.0)
    sell = pd.to_numeric(out[sell_col], errors="coerce").fillna(0.0)
    total = (buy + sell).replace(0, pd.NA)

    out["orderbook_strength"] = (buy / total).fillna(0)
    out["orderbook_imbalance"] = ((buy - sell) / total).fillna(0)

    if "date" in out.columns:
        out["_date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["_date"])
    else:
        out["_date"] = pd.RangeIndex(start=0, stop=len(out), step=1)

    group_cols = ["symbol"] if "symbol" in out.columns else []
    out = out.sort_values(group_cols + ["_date"])

    def _compute(group: pd.DataFrame) -> pd.DataFrame:
        strength = group["orderbook_strength"].astype(float)
        roll = strength.rolling(window=window, min_periods=1)
        mean = roll.mean()
        std = roll.std(ddof=0).replace(0, pd.NA)
        min_v = roll.min()
        max_v = roll.max()
        denom = (max_v - min_v).replace(0, pd.NA)

        orderbook_z = (strength - mean) / std
        orderbook_norm = (strength - min_v) / denom
        group["orderbook_z"] = pd.to_numeric(orderbook_z, errors="coerce").fillna(0.0)
        group["orderbook_norm"] = pd.to_numeric(orderbook_norm, errors="coerce").fillna(0.0)
        return group

    if group_cols:
        out = out.groupby(group_cols, group_keys=False).apply(
            _compute, include_groups=False
        )
    else:
        out = _compute(out)

    out = out.drop(columns=["_date"])
    return out
