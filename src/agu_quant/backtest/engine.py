from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable, Optional

import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    metrics: Dict[str, float]


@dataclass(frozen=True)
class MultiBacktestResult:
    equity_curve: pd.DataFrame
    metrics: Dict[str, float]
    per_symbol_metrics: Dict[str, Dict[str, float]]
    trades: pd.DataFrame


def _max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    cum_max = series.cummax()
    drawdown = (series - cum_max) / cum_max
    return float(drawdown.min())


def backtest_from_positions(
    bars: pd.DataFrame,
    positions: pd.Series,
    commission_bps: float = 1.0,
    slippage_bps: float = 1.0,
    stamp_tax_bps: float = 10.0,
    transfer_fee_bps: float = 0.0,
    annual_days: int = 252,
    apply_limit_rules: bool = True,
    limit_up_thres: float = 0.095,
    limit_down_thres: float = -0.095,
) -> BacktestResult:
    """
    基于日线的简化回测。
    - bars 需要包含 date, close
    - positions 为与 date 对齐的仓位（0-1）
    - fee_bps/slippage_bps 为单边成本（bp）
    """
    if bars is None or bars.empty:
        return BacktestResult(equity_curve=pd.DataFrame(), metrics={})

    df = bars.sort_values("date").copy()
    keep_cols = ["date", "close"]
    if "pct_chg" in df.columns:
        keep_cols.append("pct_chg")
    df = df[keep_cols].copy()
    df["ret"] = df["close"].pct_change().fillna(0.0)

    pos_target = positions.reindex(df["date"]).fillna(0.0).clip(0.0, 1.0)
    df["pos"] = pos_target.values

    if apply_limit_rules and "pct_chg" in df.columns:
        df["pos_prev"] = df["pos"].shift(1).fillna(0.0)
        buy_block = (df["pos"] > df["pos_prev"]) & (df["pct_chg"] >= limit_up_thres)
        sell_block = (df["pos"] < df["pos_prev"]) & (df["pct_chg"] <= limit_down_thres)
        df.loc[buy_block | sell_block, "pos"] = df.loc[buy_block | sell_block, "pos_prev"]

    # 交易成本：持仓变化时扣除
    df["pos_prev"] = df["pos"].shift(1).fillna(0.0)
    trade_dir = df["pos"] - df["pos_prev"]
    turnover = trade_dir.abs()
    sell_turnover = (-trade_dir).clip(lower=0.0)

    cost_bps = commission_bps + slippage_bps + transfer_fee_bps
    cost = cost_bps / 10000.0
    stamp_tax = stamp_tax_bps / 10000.0
    total_cost = turnover * cost + sell_turnover * stamp_tax

    df["net_ret"] = df["ret"] * df["pos"] - total_cost

    df["equity"] = (1.0 + df["net_ret"]).cumprod()

    total_return = float(df["equity"].iloc[-1] - 1.0)
    ann_return = float((1.0 + total_return) ** (annual_days / max(len(df), 1)) - 1.0)
    max_dd = _max_drawdown(df["equity"])
    vol = float(df["net_ret"].std() * (annual_days**0.5)) if len(df) > 1 else 0.0
    sharpe = float(ann_return / vol) if vol > 0 else 0.0

    metrics = {
        "total_return": total_return,
        "annual_return": ann_return,
        "max_drawdown": max_dd,
        "volatility": vol,
        "sharpe": sharpe,
    }

    return BacktestResult(equity_curve=df, metrics=metrics)


def backtest_multi_positions(
    bars_by_symbol: Dict[str, pd.DataFrame],
    positions_by_symbol: Dict[str, pd.Series],
    commission_bps: float = 1.0,
    slippage_bps: float = 1.0,
    stamp_tax_bps: float = 10.0,
    transfer_fee_bps: float = 0.0,
    annual_days: int = 252,
    weights: Dict[str, float] | None = None,
    weights_by_symbol: Dict[str, pd.Series] | None = None,
    apply_limit_rules: bool = True,
    limit_up_thres: float = 0.095,
    limit_down_thres: float = -0.095,
) -> MultiBacktestResult:
    """
    多标的组合回测（等权合成）。
    - bars_by_symbol: symbol -> 日线数据（含 date, close）
    - positions_by_symbol: symbol -> 与 date 对齐的仓位（0-1）
    """
    if not bars_by_symbol:
        return MultiBacktestResult(equity_curve=pd.DataFrame(), metrics={}, per_symbol_metrics={})

    per_symbol_curves: List[pd.DataFrame] = []
    per_symbol_metrics: Dict[str, Dict[str, float]] = {}
    trades_frames: List[pd.DataFrame] = []

    if weights is None:
        weights = {k: 1.0 for k in bars_by_symbol.keys()}
    weight_sum = sum(weights.values()) if weights else 1.0

    for symbol, bars in bars_by_symbol.items():
        if bars is None or bars.empty:
            continue
        positions = positions_by_symbol.get(symbol, pd.Series(dtype=float))
        bars = _align_trading_days(bars, symbol)
        result = backtest_from_positions(
            bars=bars,
            positions=positions,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            stamp_tax_bps=stamp_tax_bps,
            transfer_fee_bps=transfer_fee_bps,
            annual_days=annual_days,
            apply_limit_rules=apply_limit_rules,
            limit_up_thres=limit_up_thres,
            limit_down_thres=limit_down_thres,
        )
        curve = result.equity_curve.copy()
        curve = curve[["date", "net_ret"]].rename(columns={"net_ret": f"net_ret_{symbol}"})
        per_symbol_curves.append(curve)
        per_symbol_metrics[symbol] = result.metrics

        trades = _positions_to_trades(bars, positions, symbol)
        trades_frames.append(trades)

    if not per_symbol_curves:
        return MultiBacktestResult(equity_curve=pd.DataFrame(), metrics={}, per_symbol_metrics={})

    merged = per_symbol_curves[0]
    for nxt in per_symbol_curves[1:]:
        merged = merged.merge(nxt, on="date", how="outer")

    merged = merged.sort_values("date").fillna(0.0)
    ret_cols = [c for c in merged.columns if c.startswith("net_ret_")]
    # 等权或自定义权重组合
    if ret_cols:
        if weights_by_symbol:
            weight_frame = []
            for symbol, series in weights_by_symbol.items():
                col = f"net_ret_{symbol}"
                if col not in merged.columns:
                    continue
                s = series.reindex(merged["date"]).fillna(0.0).clip(lower=0.0)
                weight_frame.append(pd.DataFrame({"date": merged["date"], col: s.values}))
            if weight_frame:
                w = weight_frame[0]
                for nxt in weight_frame[1:]:
                    w = w.merge(nxt, on="date", how="outer")
                w = w.fillna(0.0)
                w_sum = w[ret_cols].sum(axis=1).replace(0.0, 1.0)
                merged["net_ret"] = (merged[ret_cols] * (w[ret_cols].div(w_sum, axis=0))).sum(axis=1)
            else:
                merged["net_ret"] = merged[ret_cols].mean(axis=1)
        else:
            weights_series = pd.Series(
                {f"net_ret_{k}": v for k, v in weights.items()}, dtype=float
            )
            weights_series = weights_series / weight_sum
            merged["net_ret"] = merged[ret_cols].mul(weights_series, axis=1).sum(axis=1)
    else:
        merged["net_ret"] = 0.0
    merged["equity"] = (1.0 + merged["net_ret"]).cumprod()

    total_return = float(merged["equity"].iloc[-1] - 1.0)
    ann_return = float((1.0 + total_return) ** (annual_days / max(len(merged), 1)) - 1.0)
    max_dd = _max_drawdown(merged["equity"])
    vol = float(merged["net_ret"].std() * (annual_days**0.5)) if len(merged) > 1 else 0.0
    sharpe = float(ann_return / vol) if vol > 0 else 0.0

    metrics = {
        "total_return": total_return,
        "annual_return": ann_return,
        "max_drawdown": max_dd,
        "volatility": vol,
        "sharpe": sharpe,
        "symbols": float(len(ret_cols)),
    }

    trades_df = pd.concat(trades_frames, ignore_index=True) if trades_frames else pd.DataFrame()

    return MultiBacktestResult(
        equity_curve=merged,
        metrics=metrics,
        per_symbol_metrics=per_symbol_metrics,
        trades=trades_df,
    )


def _positions_to_trades(
    bars: pd.DataFrame,
    positions: pd.Series,
    symbol: str,
) -> pd.DataFrame:
    if bars is None or bars.empty:
        return pd.DataFrame()

    df = bars.sort_values("date").copy()
    pos = positions.reindex(df["date"]).fillna(0.0).clip(0.0, 1.0)
    df["pos"] = pos.values
    df["pos_prev"] = df["pos"].shift(1).fillna(0.0)

    trades: List[Dict[str, float]] = []
    entry_date = None
    entry_price = None

    for _, row in df.iterrows():
        date = row["date"]
        if row["pos_prev"] == 0.0 and row["pos"] > 0.0:
            entry_date = date
            entry_price = row["close"]
        elif row["pos_prev"] > 0.0 and row["pos"] == 0.0 and entry_date is not None:
            exit_date = date
            exit_price = row["close"]
            ret = (exit_price - entry_price) / entry_price if entry_price else 0.0
            trades.append(
                {
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "exit_date": exit_date,
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "return": float(ret),
                }
            )
            entry_date = None
            entry_price = None

    return pd.DataFrame(trades)


def _align_trading_days(bars: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    简单的交易日对齐：去重、按日期排序，填充缺失字段为空。
    对停牌/无交易日只保留已有数据（不做插值）。
    """
    if bars is None or bars.empty:
        return bars
    df = bars.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.drop_duplicates(subset=["date"]).sort_values("date")
    return df
