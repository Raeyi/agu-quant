from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import time

import pandas as pd

from agu_quant.data.cache import CacheStore
from agu_quant.data.models import infer_exchange, normalize_symbol, symbol_to_code
from agu_quant.data.schema import (
    merge_daily_bars,
    normalize_daily_bars,
    validate_daily_bars,
)


@dataclass
class AkShareClient:
    cache_dir: Optional[Path] = None
    use_cache: bool = True
    verbose: bool = False
    retries: int = 2
    retry_backoff_sec: float = 1.5

    def _cache(self) -> Optional[CacheStore]:
        if self.cache_dir is None:
            return None
        return CacheStore(self.cache_dir)

    def _normalize_adjust(self, adjust: str) -> tuple[str, str]:
        """
        统一复权口径。
        返回: (标准口径, AkShare 口径)
        """
        if adjust is None:
            return ("qfq", "qfq")

        raw = str(adjust).strip().lower()
        if raw in ("qfq", "hfq"):
            return (raw, raw)
        if raw in ("none", "raw", ""):
            return ("none", "")
        raise ValueError(f"不支持的复权口径: {adjust}")

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
        date（交易日）
        open（开盘价）
        high（最高价）
        low（最低价）
        close（收盘价）
        volume（成交量，股/手，取决于数据源口径）
        amount（成交额，元）
        amplitude（振幅，百分比）
        pct_chg（涨跌幅，百分比）
        turnover（换手率，百分比）
        symbol（标准化代码，如 000001.SZ）
        code（纯数字代码，如 000001）
        exchange（交易所，如 SZ/SH/BJ）
        """
        import akshare as ak

        adj_method, ak_adjust = self._normalize_adjust(adjust)
        code = symbol_to_code(symbol)
        start_date = start.replace("-", "")
        end_date = end.replace("-", "")

        cache_key = f"akshare_daily::{code}::{start_date}::{end_date}::{adj_method}"
        store = self._cache()
        cached = None
        if self.use_cache and store is not None:
            cached = store.load(cache_key)
            if cached is not None and not cached.empty:
                cached = normalize_daily_bars(cached)
                if "adj_method" not in cached.columns:
                    cached["adj_method"] = adj_method
                if self.verbose:
                    print(f"[cache hit] {cache_key}")
            elif self.verbose:
                print(f"[cache miss] {cache_key}")

        last_exc: Optional[Exception] = None
        attempts = max(1, self.retries + 1)
        def _to_standard(raw_df: pd.DataFrame) -> pd.DataFrame:
            if raw_df is None or raw_df.empty:
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
                        "symbol",
                        "code",
                        "exchange",
                        "adj_method",
                    ]
                )

            df = raw_df.rename(
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
            df["adj_method"] = adj_method

            df = normalize_daily_bars(df)
            return df

        def _fetch_range(start_dt: str, end_dt: str) -> pd.DataFrame:
            nonlocal last_exc
            if self.verbose:
                print(f"[fetch] {code} {start_dt} ~ {end_dt} ({adj_method})")
            for i in range(attempts):
                try:
                    raw = ak.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date=start_dt,
                        end_date=end_dt,
                        adjust=ak_adjust,
                        timeout=timeout,
                    )
                    last_exc = None
                    return _to_standard(raw)
                except Exception as exc:
                    last_exc = exc
                    if i < attempts - 1:
                        time.sleep(self.retry_backoff_sec * (i + 1))
                        continue
            return pd.DataFrame()

        # 增量更新：优先复用缓存，必要时仅补缺失区间
        frames = []
        if cached is not None and not cached.empty:
            frames.append(cached)

            start_ts = pd.to_datetime(start, errors="coerce")
            end_ts = pd.to_datetime(end, errors="coerce")
            cached_dates = pd.to_datetime(cached["date"], errors="coerce").dropna()

            if not cached_dates.empty and pd.notna(start_ts) and pd.notna(end_ts):
                min_dt = cached_dates.min()
                max_dt = cached_dates.max()

                if start_ts < min_dt:
                    left_start = start_ts.strftime("%Y%m%d")
                    left_end = (min_dt - pd.Timedelta(days=1)).strftime("%Y%m%d")
                    if left_start <= left_end:
                        frames.append(_fetch_range(left_start, left_end))

                if end_ts > max_dt:
                    right_start = (max_dt + pd.Timedelta(days=1)).strftime("%Y%m%d")
                    right_end = end_ts.strftime("%Y%m%d")
                    if right_start <= right_end:
                        frames.append(_fetch_range(right_start, right_end))
        else:
            frames.append(_fetch_range(start_date, end_date))

        if last_exc is not None and all(f is None or f.empty for f in frames):
            if self.use_cache and allow_cache_fallback and store is not None:
                cached = store.load(cache_key)
                if cached is not None:
                    return cached
            raise RuntimeError(
                "AkShare 拉取失败，可能是网络超时或数据源不可达。"
                "请检查网络/代理，或稍后重试。"
            ) from last_exc

        if len(frames) == 1:
            df = frames[0]
        else:
            df = merge_daily_bars(
                frames[0], pd.concat(frames[1:], ignore_index=True)
            )

        if df is None or df.empty:
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
                    "symbol",
                    "code",
                    "exchange",
                    "adj_method",
                ]
            )

        # 按请求区间过滤
        start_ts = pd.to_datetime(start, errors="coerce")
        end_ts = pd.to_datetime(end, errors="coerce")
        if pd.notna(start_ts) and pd.notna(end_ts):
            dates = pd.to_datetime(df["date"], errors="coerce")
            mask = (dates >= start_ts) & (dates <= end_ts)
            df = df.loc[mask].copy()

        validate_daily_bars(df)

        if self.use_cache and store is not None:
            store.save(cache_key, df)

        return df
