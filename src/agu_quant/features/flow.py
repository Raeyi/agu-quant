from __future__ import annotations

import pandas as pd


def _count_unique_stocks(series: pd.Series) -> int:
    items = set()
    for val in series.dropna().astype(str).tolist():
        if not val:
            continue
        parts = [p for p in val.replace(",", " ").split() if p]
        items.update(parts)
    return len(items)


def compute_lhb_institution_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算龙虎榜机构席位日度净买卖统计。
    输入字段（标准化）:
    date, code, name, inst_buy, inst_sell, inst_net, reason
    输出字段:
    date, inst_buy, inst_sell, inst_net, rows, code_count
    """
    if df is None or df.empty:
        return pd.DataFrame(
            columns=["date", "inst_buy", "inst_sell", "inst_net", "rows", "code_count"]
        )

    g = df.groupby("date")
    out = g.agg(
        inst_buy=("inst_buy", "sum"),
        inst_sell=("inst_sell", "sum"),
        inst_net=("inst_net", "sum"),
        rows=("code", "count"),
        code_count=("code", "nunique"),
    ).reset_index()
    return out


def compute_lhb_institution_by_code(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算龙虎榜机构席位按股票维度的日度净买卖。
    输出字段:
    date, code, inst_buy, inst_sell, inst_net
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "code", "inst_buy", "inst_sell", "inst_net"])

    g = df.groupby(["date", "code"])
    out = g.agg(
        inst_buy=("inst_buy", "sum"),
        inst_sell=("inst_sell", "sum"),
        inst_net=("inst_net", "sum"),
    ).reset_index()
    return out


def compute_lhb_broker_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute LHB broker (yyb) daily net statistics.
    Input columns (standardized):
    date, code, name, broker, buy, sell, net, reason
    Output columns:
    date, buy, sell, net, rows, broker_count, code_count
    """
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "buy",
                "sell",
                "net",
                "rows",
                "broker_count",
                "code_count",
            ]
        )

    g = df.groupby("date")
    out = g.agg(
        buy=("buy", "sum"),
        sell=("sell", "sum"),
        net=("net", "sum"),
        rows=("broker", "count"),
        broker_count=("broker", "nunique"),
    ).reset_index()

    if "code" in df.columns:
        code_counts = g["code"].nunique().reset_index(name="code_count")
    elif "stocks" in df.columns:
        code_counts = g["stocks"].apply(_count_unique_stocks).reset_index(name="code_count")
    else:
        code_counts = out[["date"]].copy()
        code_counts["code_count"] = 0

    out = out.merge(code_counts, on="date", how="left")
    return out


def compute_lhb_broker_by_broker(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute LHB broker (yyb) stats by broker per day.
    Output columns:
    date, broker, buy, sell, net, rows, code_count
    """
    if df is None or df.empty:
        return pd.DataFrame(
            columns=["date", "broker", "buy", "sell", "net", "rows", "code_count"]
        )

    g = df.groupby(["date", "broker"])
    out = g.agg(
        buy=("buy", "sum"),
        sell=("sell", "sum"),
        net=("net", "sum"),
        rows=("broker", "count"),
    ).reset_index()

    if "code" in df.columns:
        code_counts = g["code"].nunique().reset_index(name="code_count")
    elif "stocks" in df.columns:
        code_counts = g["stocks"].apply(_count_unique_stocks).reset_index(name="code_count")
    else:
        code_counts = out[["date", "broker"]].copy()
        code_counts["code_count"] = 0

    out = out.merge(code_counts, on=["date", "broker"], how="left")
    return out


def compute_lhb_broker_heat_panel(
    df: pd.DataFrame, window: int = 20
) -> pd.DataFrame:
    """
    Compute broker heat panel over the most recent N trading dates.
    Output columns:
    broker, buy, sell, net, turnover, rows, code_count, active_days,
    avg_net, avg_turnover, buy_ratio
    """
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "broker",
                "buy",
                "sell",
                "net",
                "turnover",
                "rows",
                "code_count",
                "active_days",
                "avg_net",
                "avg_turnover",
                "buy_ratio",
            ]
        )

    tmp = df.copy()
    tmp["_date"] = pd.to_datetime(tmp["date"], errors="coerce")
    tmp = tmp.dropna(subset=["_date"])
    if tmp.empty:
        return pd.DataFrame(
            columns=[
                "broker",
                "buy",
                "sell",
                "net",
                "turnover",
                "rows",
                "code_count",
                "active_days",
                "avg_net",
                "avg_turnover",
                "buy_ratio",
            ]
        )

    unique_dates = sorted(tmp["_date"].unique())
    if window and window > 0:
        use_dates = unique_dates[-window:]
    else:
        use_dates = unique_dates

    panel_df = tmp[tmp["_date"].isin(use_dates)]
    g = panel_df.groupby("broker")
    out = g.agg(
        buy=("buy", "sum"),
        sell=("sell", "sum"),
        net=("net", "sum"),
        rows=("broker", "count"),
        active_days=("_date", "nunique"),
    ).reset_index()

    if "code" in panel_df.columns:
        code_counts = g["code"].nunique().reset_index(name="code_count")
    elif "stocks" in panel_df.columns:
        code_counts = g["stocks"].apply(_count_unique_stocks).reset_index(name="code_count")
    else:
        code_counts = out[["broker"]].copy()
        code_counts["code_count"] = 0

    out = out.merge(code_counts, on="broker", how="left")

    out["turnover"] = out["buy"] + out["sell"]
    denom_days = out["active_days"].replace(0, pd.NA)
    out["avg_net"] = (out["net"] / denom_days).fillna(0)
    out["avg_turnover"] = (out["turnover"] / denom_days).fillna(0)
    denom_turnover = out["turnover"].replace(0, pd.NA)
    out["buy_ratio"] = (out["buy"] / denom_turnover).fillna(0)
    return out
