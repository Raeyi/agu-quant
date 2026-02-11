from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any


@dataclass(frozen=True)
class ScoringConfig:
    base_score: float = 50.0
    ret_3d_pos: float = 0.03
    ret_3d_neg: float = -0.03
    ret_10d_pos: float = 0.05
    ret_10d_neg: float = -0.05
    avg_amount_5d_high: float = 5e8
    vol_5d_high: float = 0.08
    drawdown_10d_deep: float = -0.08

    w_ret_3d_pos: float = 10.0
    w_ret_3d_neg: float = -10.0
    w_ret_10d_pos: float = 8.0
    w_ret_10d_neg: float = -8.0
    w_amount_high: float = 8.0
    w_amount_low: float = -4.0
    w_drawdown_deep: float = 6.0
    w_vol_high: float = -6.0

    min_score: float = 0.0
    max_score: float = 100.0
    rule_enabled: Dict[str, bool] = field(
        default_factory=lambda: {
            "ret_3d_pos": True,
            "ret_3d_neg": True,
            "ret_10d_pos": True,
            "ret_10d_neg": True,
            "amount_high": True,
            "amount_low": True,
            "drawdown_deep": True,
            "vol_high": True,
        }
    )
    reason_templates: Dict[str, str] = field(
        default_factory=lambda: {
            "ret_3d_pos": "近3日涨幅 {ret_3d:.2%} 强势",
            "ret_3d_neg": "近3日回撤 {ret_3d:.2%} 偏弱",
            "ret_10d_pos": "近10日趋势向上 {ret_10d:.2%}",
            "ret_10d_neg": "近10日趋势向下 {ret_10d:.2%}",
            "amount_high": "5日成交额均值 {avg_amount_5d:.0f} 偏高",
            "amount_low": "5日成交额均值 {avg_amount_5d:.0f} 偏低",
            "drawdown_deep": "10日回撤 {drawdown_10d:.2%} 偏深",
            "vol_high": "5日波动 {vol_5d:.2%} 偏高",
        }
    )

    @staticmethod
    def from_json(path: Path) -> "ScoringConfig":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return ScoringConfig(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_score": self.base_score,
            "ret_3d_pos": self.ret_3d_pos,
            "ret_3d_neg": self.ret_3d_neg,
            "ret_10d_pos": self.ret_10d_pos,
            "ret_10d_neg": self.ret_10d_neg,
            "avg_amount_5d_high": self.avg_amount_5d_high,
            "vol_5d_high": self.vol_5d_high,
            "drawdown_10d_deep": self.drawdown_10d_deep,
            "w_ret_3d_pos": self.w_ret_3d_pos,
            "w_ret_3d_neg": self.w_ret_3d_neg,
            "w_ret_10d_pos": self.w_ret_10d_pos,
            "w_ret_10d_neg": self.w_ret_10d_neg,
            "w_amount_high": self.w_amount_high,
            "w_amount_low": self.w_amount_low,
            "w_drawdown_deep": self.w_drawdown_deep,
            "w_vol_high": self.w_vol_high,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "rule_enabled": self.rule_enabled,
            "reason_templates": self.reason_templates,
        }
