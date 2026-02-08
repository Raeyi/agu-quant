from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import json

import pandas as pd

from agu_quant.backtest import MultiBacktestResult


@dataclass(frozen=True)
class BacktestReport:
    metrics: Dict[str, float]
    per_symbol_metrics: Dict[str, Dict[str, float]]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    stats: Dict[str, float]

    def save(self, out_dir: Path, prefix: str = "backtest") -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        curve_path = out_dir / f"{prefix}_equity.csv"
        metrics_path = out_dir / f"{prefix}_metrics.json"
        trades_path = out_dir / f"{prefix}_trades.csv"
        stats_path = out_dir / f"{prefix}_stats.json"

        self.equity_curve.to_csv(curve_path, index=False)
        self.trades.to_csv(trades_path, index=False)
        payload = {
            "metrics": self.metrics,
            "per_symbol_metrics": self.per_symbol_metrics,
        }
        metrics_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        stats_path.write_text(json.dumps(self.stats, ensure_ascii=False, indent=2), encoding="utf-8")


def report_from_multi(result: MultiBacktestResult) -> BacktestReport:
    stats = _trade_stats(result.trades)
    return BacktestReport(
        metrics=result.metrics,
        per_symbol_metrics=result.per_symbol_metrics,
        equity_curve=result.equity_curve,
        trades=result.trades,
        stats=stats,
    )


def _trade_stats(trades: pd.DataFrame) -> Dict[str, float]:
    if trades is None or trades.empty:
        return {
            "trades": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
        }

    wins = trades[trades["return"] > 0]
    losses = trades[trades["return"] <= 0]
    win_rate = len(wins) / len(trades) if len(trades) else 0.0
    avg_win = wins["return"].mean() if len(wins) else 0.0
    avg_loss = losses["return"].mean() if len(losses) else 0.0
    profit_factor = (
        wins["return"].sum() / abs(losses["return"].sum())
        if len(losses) and abs(losses["return"].sum()) > 0
        else 0.0
    )

    avg_hold_days = 0.0
    if "entry_date" in trades.columns and "exit_date" in trades.columns:
        hold_days = (
            pd.to_datetime(trades["exit_date"]) - pd.to_datetime(trades["entry_date"])
        ).dt.days
        avg_hold_days = hold_days.mean() if len(hold_days) else 0.0

    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    return {
        "trades": float(len(trades)),
        "win_rate": float(win_rate),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "profit_factor": float(profit_factor),
        "avg_hold_days": float(avg_hold_days),
        "expectancy": float(expectancy),
    }
