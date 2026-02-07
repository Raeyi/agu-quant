from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import pandas as pd

from agu_quant.data import AkShareClient, normalize_symbol
from agu_quant.signals.scoring import score_daily_bars, ScoreResult
from agu_quant.signals.scoring_config import ScoringConfig


@dataclass(frozen=True)
class CandidateRow:
    symbol: str
    score: float
    suggested_position: float
    reason: str
    ret_3d: float
    ret_10d: float
    avg_amount_5d: float
    vol_5d: float
    drawdown_10d: float


def build_candidate_pool(
    symbols: Iterable[str],
    start: str,
    end: str,
    client: AkShareClient,
    config: ScoringConfig | None = None,
) -> pd.DataFrame:
    rows: List[CandidateRow] = []

    for s in symbols:
        symbol = normalize_symbol(s)
        bars = client.daily_bars(symbol, start=start, end=end)
        result: ScoreResult = score_daily_bars(bars, config=config)
        rows.append(
            CandidateRow(
                symbol=symbol,
                score=result.score,
                suggested_position=result.suggested_position,
                reason=";".join(result.reasons),
                ret_3d=result.metrics.get("ret_3d", 0.0),
                ret_10d=result.metrics.get("ret_10d", 0.0),
                avg_amount_5d=result.metrics.get("avg_amount_5d", 0.0),
                vol_5d=result.metrics.get("vol_5d", 0.0),
                drawdown_10d=result.metrics.get("drawdown_10d", 0.0),
            )
        )

    df = pd.DataFrame([r.__dict__ for r in rows])
    if not df.empty:
        df = df.sort_values(["score", "symbol"], ascending=[False, True])
    return df
