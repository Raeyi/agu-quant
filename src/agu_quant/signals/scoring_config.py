from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


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

    @staticmethod
    def from_json(path: Path) -> "ScoringConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return ScoringConfig(**data)

    def to_dict(self) -> Dict[str, float]:
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
        }
