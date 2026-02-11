from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Dict, Optional

import pandas as pd

from agu_quant.data import AkShareClient, normalize_symbol
from agu_quant.features.limitup import add_limit_up_flags, consecutive_limit_up
from agu_quant.features.patterns import add_pattern_flags
from agu_quant.features.technical import add_turnover_standardized
from agu_quant.signals.scoring import score_daily_bars, ScoreResult
from agu_quant.signals.scoring_config import ScoringConfig
from agu_quant.youzi import build_youzi_hits, YouziHit


@dataclass(frozen=True)
class CandidateRow:
    symbol: str
    date: str
    close: float
    pct_chg: float
    turnover: float
    amount: float
    industry: str
    industry_consecutive: int
    youzi_hit: int
    youzi_brokers: str
    limit_up: int
    broken_limit_up: int
    consecutive: int
    breakout_volume: int
    turnover_board: int
    one_word_board: int
    shrink_volume_board: int
    turnover_z: float
    turnover_norm: float
    turnover_pct_rank: float
    score: float
    suggested_position: float
    reason: str
    ret_3d: float
    ret_10d: float
    ret_20d: float
    avg_amount_5d: float
    vol_5d: float
    drawdown_10d: float


def _latest_snapshot(bars: pd.DataFrame) -> dict:
    if bars is None or bars.empty:
        return {}

    df = bars.sort_values("date").copy()
    df = add_limit_up_flags(df)
    if "limit_up" in df.columns:
        df["consecutive"] = consecutive_limit_up(df)

    patterned = add_pattern_flags(df)
    if patterned is not None and not patterned.empty:
        df = patterned

    standardized = add_turnover_standardized(df) if "turnover" in df.columns else pd.DataFrame()
    if standardized is not None and not standardized.empty:
        df = standardized

    last = df.iloc[-1]

    def _get(col: str, default: float = 0.0) -> float:
        if col in last and pd.notna(last[col]):
            return float(last[col])
        return default

    return {
        "date": str(last.get("date", "")),
        "close": _get("close"),
        "pct_chg": _get("pct_chg"),
        "turnover": _get("turnover"),
        "amount": _get("amount"),
        "limit_up": int(_get("limit_up")),
        "broken_limit_up": int(_get("broken_limit_up")),
        "consecutive": int(_get("consecutive")),
        "breakout_volume": int(_get("breakout_volume")),
        "turnover_board": int(_get("turnover_board")),
        "one_word_board": int(_get("one_word_board")),
        "shrink_volume_board": int(_get("shrink_volume_board")),
        "turnover_z": _get("turnover_z"),
        "turnover_norm": _get("turnover_norm"),
        "turnover_pct_rank": _get("turnover_pct_rank"),
    }


def build_candidate_pool(
    symbols: Iterable[str],
    start: str,
    end: str,
    client: AkShareClient,
    config: ScoringConfig | None = None,
    industry_map: Optional[Dict[str, str]] = None,
    broker_active_df: Optional[pd.DataFrame] = None,
    youzi_whitelist: Optional[List[str]] = None,
) -> pd.DataFrame:
    rows: List[CandidateRow] = []
    industry_map = industry_map or {}
    youzi_whitelist = youzi_whitelist or []

    # 预计算行业内连板高度（以最近交易日的连板数为准）
    industry_latest_consecutive: Dict[str, int] = {}
    for s in symbols:
        symbol = normalize_symbol(s)
        industry = industry_map.get(symbol, "")
        if not industry:
            continue
        bars = client.daily_bars(symbol, start=start, end=end)
        if bars is None or bars.empty:
            continue
        df = add_limit_up_flags(bars)
        df["consecutive"] = consecutive_limit_up(df)
        latest = int(df.sort_values("date")["consecutive"].iloc[-1])
        industry_latest_consecutive[industry] = max(
            industry_latest_consecutive.get(industry, 0), latest
        )

    youzi_hits_by_symbol: Dict[str, YouziHit] = {}
    for s in symbols:
        symbol = normalize_symbol(s)
        if not youzi_hits_by_symbol:
            # Use latest available date from each symbol to compute hits (if data provided)
            if broker_active_df is not None and not broker_active_df.empty:
                bars = client.daily_bars(symbol, start=start, end=end)
                if bars is not None and not bars.empty:
                    latest_date = str(bars.sort_values("date")["date"].iloc[-1])
                    youzi_hits_by_symbol = build_youzi_hits(
                        broker_active_df, youzi_whitelist, latest_date
                    )

    for s in symbols:
        symbol = normalize_symbol(s)
        industry = industry_map.get(symbol, "")
        bars = client.daily_bars(symbol, start=start, end=end)
        result: ScoreResult = score_daily_bars(bars, config=config)
        snapshot = _latest_snapshot(bars)
        ret_20d = 0.0
        if bars is not None and not bars.empty:
            close = bars.sort_values("date")["close"]
            ret_20d = (
                (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21]
                if len(close) >= 21
                else 0.0
            )
        rows.append(
            CandidateRow(
                symbol=symbol,
                date=snapshot.get("date", ""),
                close=snapshot.get("close", 0.0),
                pct_chg=snapshot.get("pct_chg", 0.0),
                turnover=snapshot.get("turnover", 0.0),
                amount=snapshot.get("amount", 0.0),
                industry=industry,
                industry_consecutive=industry_latest_consecutive.get(industry, 0),
                youzi_hit=youzi_hits_by_symbol.get(symbol, YouziHit(0, [])).hit,
                youzi_brokers=";".join(youzi_hits_by_symbol.get(symbol, YouziHit(0, [])).brokers),
                limit_up=snapshot.get("limit_up", 0),
                broken_limit_up=snapshot.get("broken_limit_up", 0),
                consecutive=snapshot.get("consecutive", 0),
                breakout_volume=snapshot.get("breakout_volume", 0),
                turnover_board=snapshot.get("turnover_board", 0),
                one_word_board=snapshot.get("one_word_board", 0),
                shrink_volume_board=snapshot.get("shrink_volume_board", 0),
                turnover_z=snapshot.get("turnover_z", 0.0),
                turnover_norm=snapshot.get("turnover_norm", 0.0),
                turnover_pct_rank=snapshot.get("turnover_pct_rank", 0.0),
                score=result.score,
                suggested_position=result.suggested_position,
                reason=";".join(result.reasons),
                ret_3d=result.metrics.get("ret_3d", 0.0),
                ret_10d=result.metrics.get("ret_10d", 0.0),
                ret_20d=float(ret_20d),
                avg_amount_5d=result.metrics.get("avg_amount_5d", 0.0),
                vol_5d=result.metrics.get("vol_5d", 0.0),
                drawdown_10d=result.metrics.get("drawdown_10d", 0.0),
            )
        )

    df = pd.DataFrame([r.__dict__ for r in rows])
    if not df.empty:
        df = df.sort_values(["score", "symbol"], ascending=[False, True])
    return df
