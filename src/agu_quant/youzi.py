from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import pandas as pd


@dataclass(frozen=True)
class YouziHit:
    hit: int
    brokers: List[str]


def load_youzi_whitelist(path: Path) -> Set[str]:
    """
    Load a youzi broker whitelist from CSV.
    Expected columns: broker
    Optional columns: alias, note, source
    """
    if path is None or not path.exists():
        return set()
    df = pd.read_csv(path)
    if df.empty or "broker" not in df.columns:
        return set()
    return set(df["broker"].dropna().astype(str).str.strip().tolist())


def _parse_stocks(raw: str) -> Set[str]:
    if not raw:
        return set()
    text = str(raw)
    parts = [p for p in text.replace(",", " ").split() if p]
    return set(parts)


def build_youzi_hits(
    broker_active_df: pd.DataFrame,
    whitelist: Iterable[str],
    date: str,
) -> Dict[str, YouziHit]:
    """
    Build per-symbol youzi hits from LHB broker active data.
    broker_active_df expects columns: date, broker, stocks (optional)
    """
    if broker_active_df is None or broker_active_df.empty:
        return {}
    if "date" not in broker_active_df.columns or "broker" not in broker_active_df.columns:
        return {}

    use = broker_active_df.copy()
    use = use[use["date"] == date]
    if use.empty:
        return {}

    if "stocks" not in use.columns:
        return {}

    wl = set([str(b).strip() for b in whitelist if b])
    hits: Dict[str, List[str]] = {}
    for _, row in use.iterrows():
        broker = str(row.get("broker", "")).strip()
        if broker not in wl:
            continue
        symbols = _parse_stocks(row.get("stocks", ""))
        for sym in symbols:
            hits.setdefault(sym, []).append(broker)

    out: Dict[str, YouziHit] = {}
    for sym, brokers in hits.items():
        uniq = sorted(set(brokers))
        out[sym] = YouziHit(hit=1, brokers=uniq)
    return out
