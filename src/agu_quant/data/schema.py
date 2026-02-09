# 标准化与校验逻辑模块
# 在 AkShare 数据源输出后统一标准化并校验
# 导出标准化工具以便后续其它数据源复用

from __future__ import annotations

from typing import Iterable

import pandas as pd

REQUIRED_DAILY_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "pct_chg",
    "turnover",
    "symbol",
    "code",
    "exchange",
]

OPTIONAL_DAILY_COLUMNS = [
    "amplitude",
    "adj_factor",
    "adj_method",
]

_NUMERIC_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "pct_chg",
    "turnover",
    "amplitude",
    "adj_factor",
]


def normalize_daily_bars(df: pd.DataFrame) -> pd.DataFrame:
    """
    归一化日线数据为统一标准格式：
    - 强制包含必需字段
    - 日期统一为 YYYY-MM-DD
    - 按日期排序，去重（同日保留最后一条）
    - 数值列强制转为浮点（如存在）
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=REQUIRED_DAILY_COLUMNS)

    out = df.copy()

    # Date normalization
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Numeric coercion
    for col in _NUMERIC_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # Drop rows with invalid dates
    out = out[out["date"].notna()]

    # Sort and de-duplicate by date
    out = out.sort_values("date").drop_duplicates(subset=["date"], keep="last")

    # 仅保留必需字段与已存在的可选字段
    keep = [c for c in REQUIRED_DAILY_COLUMNS if c in out.columns]
    keep += [c for c in OPTIONAL_DAILY_COLUMNS if c in out.columns]
    out = out[keep]

    return out


def validate_daily_bars(df: pd.DataFrame, required: Iterable[str] = None) -> None:
    """
    校验日线数据的字段与基础完整性。
    校验失败将抛出 ValueError。
    """
    if df is None:
        raise ValueError("daily_bars is None")

    required_cols = list(required) if required is not None else REQUIRED_DAILY_COLUMNS
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    if df.empty:
        return

    # Check date monotonicity (non-decreasing)
    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("invalid date values found after normalization")
    if not dates.is_monotonic_increasing:
        raise ValueError("date is not sorted ascending")


def build_quality_report(
    df: pd.DataFrame,
    calendar: Iterable[str] | None = None,
    date_col: str = "date",
) -> dict:
    """
    生成数据质量报告，便于缺口记录与监控。
    返回字段：
    - rows: 总行数（总行数）
    - missing_dates: 缺失交易日数量（缺失交易日数，需提供 calendar）
    - duplicate_dates: 重复日期数量（重复日期数）
    - invalid_dates: 无法解析的日期数量（无效日期数）
    - missing_rate: 缺失交易日比例（缺失比例，需提供 calendar）
    - first_date: 起始日期（首日）
    - last_date: 结束日期（末日）
    - nan_ratio: 数值列缺失比例（平均缺失率）
    - outlier_count: 数值列异常值数量（基础异常值数）
    """
    if df is None:
        return {
            "rows": 0,
            "missing_dates": None,
            "duplicate_dates": 0,
            "invalid_dates": 0,
            "missing_rate": None,
            "first_date": None,
            "last_date": None,
            "nan_ratio": None,
            "outlier_count": 0,
        }

    rows = len(df)
    if date_col not in df.columns:
        return {
            "rows": rows,
            "missing_dates": None,
            "duplicate_dates": 0,
            "invalid_dates": rows,
            "missing_rate": None,
            "first_date": None,
            "last_date": None,
            "nan_ratio": None,
            "outlier_count": 0,
        }

    dates = pd.to_datetime(df[date_col], errors="coerce")
    invalid_dates = int(dates.isna().sum())
    duplicate_dates = int(dates.duplicated().sum())

    missing_dates = None
    missing_rate = None
    if calendar is not None:
        cal = pd.to_datetime(list(calendar), errors="coerce")
        cal = cal.dropna()
        data_dates = dates.dropna().dt.strftime("%Y-%m-%d")
        cal_dates = cal.dt.strftime("%Y-%m-%d")
        missing_dates = int(len(set(cal_dates) - set(data_dates)))
        if len(cal_dates) > 0:
            missing_rate = missing_dates / len(set(cal_dates))

    first_date = None
    last_date = None
    valid_dates = dates.dropna()
    if not valid_dates.empty:
        first_date = valid_dates.min().strftime("%Y-%m-%d")
        last_date = valid_dates.max().strftime("%Y-%m-%d")

    numeric_cols = [c for c in ["pct_chg", "turnover"] if c in df.columns]
    nan_ratio = None
    outlier_count = 0
    if numeric_cols:
        numeric_df = df[numeric_cols]
        nan_ratio = float(numeric_df.isna().mean().mean())
        outlier_count = _basic_outlier_count(numeric_df)

    return {
        "rows": rows,
        "missing_dates": missing_dates,
        "duplicate_dates": duplicate_dates,
        "invalid_dates": invalid_dates,
        "missing_rate": missing_rate,
        "first_date": first_date,
        "last_date": last_date,
        "nan_ratio": nan_ratio,
        "outlier_count": outlier_count,
    }


def _basic_outlier_count(df: pd.DataFrame) -> int:
    """
    基础异常值检测：使用 IQR 方法统计异常值数量（越小越好）。
    """
    count = 0
    for col in df.columns:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count += int(((series < lower) | (series > upper)).sum())
    return count


def merge_daily_bars(
    base: pd.DataFrame | None, incoming: pd.DataFrame | None
) -> pd.DataFrame:
    """
    合并两份日线数据，按日期去重（同日保留最后一条）。
    """
    if base is None or base.empty:
        return incoming.copy() if incoming is not None else pd.DataFrame()
    if incoming is None or incoming.empty:
        return base.copy()

    merged = pd.concat([base, incoming], ignore_index=True)
    merged = normalize_daily_bars(merged)
    return merged
