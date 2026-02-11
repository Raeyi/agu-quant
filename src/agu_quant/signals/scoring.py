from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from agu_quant.signals.scoring_config import ScoringConfig


@dataclass(frozen=True)
class ScoreResult:
    score: float
    suggested_position: float
    reasons: List[str]
    metrics: Dict[str, float]


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _format_reason(template: str, metrics: Dict[str, float]) -> str:
    try:
        return template.format(**metrics)
    except Exception:
        return template


def score_daily_bars(df: pd.DataFrame, config: ScoringConfig | None = None) -> ScoreResult:
    """
    基于日线数据的轻量评分骨架（教育用途）。
    评分区间: 0-100，建议仓位区间: 0-1（仅作参考）。
    """
    if config is None:
        config = ScoringConfig()
    if df is None or df.empty:
        return ScoreResult(score=0.0, suggested_position=0.0, reasons=["无数据"], metrics={})

    data = df.sort_values("date").copy()

    # 基础指标
    close = data["close"]
    high = data["high"]
    low = data["low"]
    amount = data["amount"]

    ret_3d = _safe_pct(close.iloc[-1] - close.iloc[-4], close.iloc[-4]) if len(close) >= 4 else 0.0
    ret_10d = _safe_pct(close.iloc[-1] - close.iloc[-11], close.iloc[-11]) if len(close) >= 11 else 0.0
    avg_amount_5d = amount.tail(5).mean() if len(amount) >= 5 else amount.mean()
    vol_5d = ((high - low) / close).tail(5).mean() if len(close) >= 5 else ((high - low) / close).mean()
    drawdown_10d = 0.0
    if len(close) >= 10:
        recent_high = close.tail(10).max()
        drawdown_10d = _safe_pct(close.iloc[-1] - recent_high, recent_high)

    metrics = {
        "ret_3d": float(ret_3d),
        "ret_10d": float(ret_10d),
        "avg_amount_5d": float(avg_amount_5d) if pd.notna(avg_amount_5d) else 0.0,
        "vol_5d": float(vol_5d) if pd.notna(vol_5d) else 0.0,
        "drawdown_10d": float(drawdown_10d),
    }

    # 规则化评分（配置化 + 可解释理由模板）
    score = config.base_score
    reasons: List[str] = []
    enabled = config.rule_enabled
    templates = config.reason_templates

    if enabled.get("ret_3d_pos", True) and ret_3d > config.ret_3d_pos:
        score += config.w_ret_3d_pos
        reasons.append(_format_reason(templates.get("ret_3d_pos", ""), metrics))
    elif enabled.get("ret_3d_neg", True) and ret_3d < config.ret_3d_neg:
        score += config.w_ret_3d_neg
        reasons.append(_format_reason(templates.get("ret_3d_neg", ""), metrics))

    if enabled.get("ret_10d_pos", True) and ret_10d > config.ret_10d_pos:
        score += config.w_ret_10d_pos
        reasons.append(_format_reason(templates.get("ret_10d_pos", ""), metrics))
    elif enabled.get("ret_10d_neg", True) and ret_10d < config.ret_10d_neg:
        score += config.w_ret_10d_neg
        reasons.append(_format_reason(templates.get("ret_10d_neg", ""), metrics))

    if enabled.get("amount_high", True) and avg_amount_5d > config.avg_amount_5d_high:
        score += config.w_amount_high
        reasons.append(_format_reason(templates.get("amount_high", ""), metrics))
    elif enabled.get("amount_low", True):
        score += config.w_amount_low
        reasons.append(_format_reason(templates.get("amount_low", ""), metrics))

    if enabled.get("drawdown_deep", True) and drawdown_10d < config.drawdown_10d_deep:
        score += config.w_drawdown_deep
        reasons.append(_format_reason(templates.get("drawdown_deep", ""), metrics))

    if enabled.get("vol_high", True) and vol_5d > config.vol_5d_high:
        score += config.w_vol_high
        reasons.append(_format_reason(templates.get("vol_high", ""), metrics))

    score = max(config.min_score, min(config.max_score, score))
    suggested_position = round(score / config.max_score, 2) if config.max_score > 0 else 0.0

    return ScoreResult(
        score=score,
        suggested_position=suggested_position,
        reasons=reasons,
        metrics=metrics,
    )
