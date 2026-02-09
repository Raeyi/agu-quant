from __future__ import annotations

from typing import Dict, Iterable, Tuple

import pandas as pd

from agu_quant.features.limitup import add_limit_up_flags


def compute_theme_panel(
    bars_by_symbol: Dict[str, pd.DataFrame],
    symbol_to_theme: Dict[str, str],
    limit_up_thres: float = 0.095,
    limit_down_thres: float = -0.095,
) -> pd.DataFrame:
    """
    计算题材/板块面板（日频）。
    输出字段（核心）:
    date, theme, total, avg_pct_chg, up, down,
    limit_up, limit_down, broken, limit_up_ratio
    """
    frames = []
    for symbol, bars in bars_by_symbol.items():
        if bars is None or bars.empty:
            continue
        theme = symbol_to_theme.get(symbol)
        if not theme:
            continue
        df = add_limit_up_flags(bars, limit_up_thres, limit_down_thres)
        df["symbol"] = symbol
        df["theme"] = theme
        df["up"] = (df["pct_chg"] > 0).astype(int)
        df["down"] = (df["pct_chg"] < 0).astype(int)
        frames.append(
            df[
                [
                    "date",
                    "symbol",
                    "theme",
                    "pct_chg",
                    "up",
                    "down",
                    "limit_up",
                    "limit_down",
                    "broken_limit_up",
                ]
            ]
        )

    if not frames:
        return pd.DataFrame()

    all_df = pd.concat(frames, ignore_index=True)
    g = all_df.groupby(["date", "theme"])
    panel = g.agg(
        total=("symbol", "count"),
        avg_pct_chg=("pct_chg", "mean"),
        up=("up", "sum"),
        down=("down", "sum"),
        limit_up=("limit_up", "sum"),
        limit_down=("limit_down", "sum"),
        broken=("broken_limit_up", "sum"),
    ).reset_index()

    panel["limit_up_ratio"] = panel["limit_up"] / panel["total"]
    return panel


def rank_themes(
    panel: pd.DataFrame,
    date: str,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    对单日题材进行排名（按平均涨幅与涨停数综合）。
    """
    if panel is None or panel.empty:
        return pd.DataFrame()
    day = panel[panel["date"] == date].copy()
    if day.empty:
        return day

    day["score"] = day["avg_pct_chg"].fillna(0) + day["limit_up"].fillna(0) * 0.5
    return day.sort_values("score", ascending=False).head(top_n)


def identify_main_theme(
    panel: pd.DataFrame,
    top_k: int = 1,
) -> pd.DataFrame:
    """
    识别主线题材：每日取综合得分最高的题材。
    输出字段: date, theme, score
    """
    if panel is None or panel.empty:
        return pd.DataFrame()

    df = panel.copy()
    df["score"] = df["avg_pct_chg"].fillna(0) + df["limit_up"].fillna(0) * 0.5

    result = []
    for date, group in df.groupby("date"):
        top = group.sort_values("score", ascending=False).head(top_k)
        for _, row in top.iterrows():
            result.append({"date": date, "theme": row["theme"], "score": row["score"]})
    return pd.DataFrame(result)


def compute_theme_rotation(
    main_theme_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    计算题材轮动：主线题材变化与持续天数。
    输出字段: date, theme, streak, changed
    """
    if main_theme_df is None or main_theme_df.empty:
        return pd.DataFrame()

    df = main_theme_df.sort_values("date").copy()
    streak = 0
    last_theme = None
    records = []
    for _, row in df.iterrows():
        theme = row["theme"]
        if theme == last_theme:
            streak += 1
            changed = 0
        else:
            streak = 1
            changed = 1
        records.append(
            {
                "date": row["date"],
                "theme": theme,
                "streak": streak,
                "changed": changed,
            }
        )
        last_theme = theme

    return pd.DataFrame(records)
