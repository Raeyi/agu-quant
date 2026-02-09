from __future__ import annotations

from typing import Protocol

import pandas as pd


class DataProvider(Protocol):
    """
    数据源统一接口，用于屏蔽不同数据源差异。
    """

    def stock_list(self) -> pd.DataFrame:
        """
        返回股票列表，标准字段：code, name, exchange, symbol。
        """

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
        返回日频行情，字段需符合 schema 标准。
        """
