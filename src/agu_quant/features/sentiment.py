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


def compute_sentiment_panel(
    bars_by_symbol: Dict[str, pd.DataFrame],
    limit_up_thres: float = 0.095,
    limit_down_thres: float = -0.095,
) -> pd.DataFrame:
    """
    计算情绪面板（日频）。
    输出字段（核心）:
    date, total, up, down, flat,
    limit_up, limit_down, broken,
    limit_up_ratio, limit_down_ratio, broken_ratio,
    first_limit_up, second_limit_up, third_plus_limit_up,
    promotion_rate, max_consecutive
    """
    frames = []
    for symbol, bars in bars_by_symbol.items():
        if bars is None or bars.empty:
            continue
        df = add_limit_up_flags(bars, limit_up_thres, limit_down_thres)
        df["consecutive"] = consecutive_limit_up(df)
        df["symbol"] = symbol

        # 涨跌家数：基于涨跌幅的方向
        df["up"] = (df["pct_chg"] > 0).astype(int)
        df["down"] = (df["pct_chg"] < 0).astype(int)
        df["flat"] = (df["pct_chg"] == 0).astype(int)

        # 连板分层：首板、二板、三板及以上
        df["first_limit_up"] = ((df["limit_up"] == 1) & (df["consecutive"] == 1)).astype(int)
        df["second_limit_up"] = ((df["limit_up"] == 1) & (df["consecutive"] == 2)).astype(int)
        df["third_plus_limit_up"] = ((df["limit_up"] == 1) & (df["consecutive"] >= 3)).astype(int)

        frames.append(
            df[
                [
                    "date",
                    "symbol",
                    "up",
                    "down",
                    "flat",
                    "limit_up",
                    "limit_down",
                    "broken_limit_up",
                    "first_limit_up",
                    "second_limit_up",
                    "third_plus_limit_up",
                    "consecutive",
                ]
            ]
        )

    if not frames:
        return pd.DataFrame()

    all_df = pd.concat(frames, ignore_index=True)
    g = all_df.groupby("date")
    panel = g.agg(
        total=("symbol", "count"),
        up=("up", "sum"),
        down=("down", "sum"),
        flat=("flat", "sum"),
        limit_up=("limit_up", "sum"),
        limit_down=("limit_down", "sum"),
        broken=("broken_limit_up", "sum"),
        first_limit_up=("first_limit_up", "sum"),
        second_limit_up=("second_limit_up", "sum"),
        third_plus_limit_up=("third_plus_limit_up", "sum"),
        max_consecutive=("consecutive", "max"),
    ).reset_index()

    panel["limit_up_ratio"] = panel["limit_up"] / panel["total"]
    panel["limit_down_ratio"] = panel["limit_down"] / panel["total"]

    denom = (panel["limit_up"] + panel["broken"]).replace(0, pd.NA)
    panel["broken_ratio"] = (panel["broken"] / denom).fillna(0)

    # 连板晋级率：二板 / 首板（避免除零）
    promo_denom = panel["first_limit_up"].replace(0, pd.NA)
    panel["promotion_rate"] = (panel["second_limit_up"] / promo_denom).fillna(0)

    return panel
