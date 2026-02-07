from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import time

import pandas as pd

from agu_quant.data.cache import CacheStore
from agu_quant.data.models import infer_exchange, normalize_symbol, symbol_to_code


@dataclass
class AkShareClient:
    cache_dir: Optional[Path] = None
    use_cache: bool = True
    retries: int = 2
    retry_backoff_sec: float = 1.5

    def _cache(self) -> Optional[CacheStore]:
        if self.cache_dir is None:
            return None
        return CacheStore(self.cache_dir)

    def stock_list(self) -> pd.DataFrame:
        """
        返回 A 股股票列表。
        输出字段: code, name, exchange, symbol
        """
        import akshare as ak

        raw = ak.stock_info_a_code_name()
        df = raw.rename(columns={"code": "code", "name": "name"}).copy()
        df["exchange"] = df["code"].map(infer_exchange)
        df["symbol"] = df["code"] + "." + df["exchange"]
        return df[["code", "name", "exchange", "symbol"]]

    def daily_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        adjust: str = "qfq",
        timeout: int = 15,
        allow_cache_fallback: bool = True,
    ) -> pd.DataFrame:
        """
        日频行情。
        输出字段:
        date, open, high, low, close, volume, amount, amplitude, pct_chg, turnover
        """
        import akshare as ak

        code = symbol_to_code(symbol)
        start_date = start.replace("-", "")
        end_date = end.replace("-", "")

        cache_key = f"akshare_daily::{code}::{start_date}::{end_date}::{adjust}"
        store = self._cache()
        if self.use_cache and store is not None:
            cached = store.load(cache_key)
            if cached is not None:
                return cached

        last_exc: Optional[Exception] = None
        attempts = max(1, self.retries + 1)
        for i in range(attempts):
            try:
                raw = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                    timeout=timeout,
                )
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if i < attempts - 1:
                    time.sleep(self.retry_backoff_sec * (i + 1))
                    continue
        if last_exc is not None:
            if self.use_cache and allow_cache_fallback and store is not None:
                cached = store.load(cache_key)
                if cached is not None:
                    return cached
            raise RuntimeError(
                "AkShare 拉取失败，可能是网络超时或数据源不可达。"
                "请检查网络/代理，或稍后重试。"
            ) from last_exc

        if raw is None or raw.empty:
            return pd.DataFrame(
                columns=[
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "amount",
                    "amplitude",
                    "pct_chg",
                    "turnover",
                ]
            )

        df = raw.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_chg",
                "换手率": "turnover",
            }
        )

        keep = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "amplitude",
            "pct_chg",
            "turnover",
        ]
        df = df[keep]
        df["symbol"] = normalize_symbol(symbol)
        df["code"] = code
        df["exchange"] = infer_exchange(code)

        if self.use_cache and store is not None:
            store.save(cache_key, df)

        return df
