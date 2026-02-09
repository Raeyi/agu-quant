from __future__ import annotations

from typing import Iterable, List, Optional

import pandas as pd


def build_trading_calendar(df: pd.DataFrame, date_col: str = "date") -> List[str]:
    """
    从数据中构建交易日历（YYYY-MM-DD 列表）。
    适用于基础版：以已有日线日期作为交易日集合。
    """
    if df is None or df.empty or date_col not in df.columns:
        return []

    dates = pd.to_datetime(df[date_col], errors="coerce")
    dates = dates.dropna().dt.strftime("%Y-%m-%d")
    return sorted(dates.unique().tolist())


def align_to_calendar(
    df: pd.DataFrame,
    calendar: Iterable[str],
    date_col: str = "date",
    fill: Optional[str] = None,
) -> pd.DataFrame:
    """
    将日线数据对齐到指定交易日历。
    - calendar: YYYY-MM-DD 列表
    - fill: None / "ffill" / "zero"
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=list(df.columns) if df is not None else [])

    if date_col not in df.columns:
        raise ValueError(f"缺少日期字段: {date_col}")

    cal = pd.to_datetime(list(calendar), errors="coerce")
    cal = cal[~pd.isna(cal)].sort_values().unique()

    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col])
    out = out.sort_values(date_col).set_index(date_col)

    out = out.reindex(cal)

    if fill == "ffill":
        out = out.ffill()
    elif fill == "zero":
        out = out.fillna(0)

    out = out.reset_index().rename(columns={"index": date_col})
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )

    return out
