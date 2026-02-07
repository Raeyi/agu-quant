from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class StockInfo:
    code: str
    name: str
    exchange: str
    symbol: str


def infer_exchange(code: str) -> str:
    """
    根据股票代码粗略推断交易所。
    6 开头一般为上交所，0/3 开头一般为深交所，8/4 可能为北交所。
    """
    if not code:
        return "UNKNOWN"
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("8", "4")):
        return "BJ"
    return "UNKNOWN"


def normalize_symbol(symbol: str) -> str:
    """
    统一为 000001.SZ 形式。
    支持输入: 000001, 000001.SZ, SZ000001, sz000001, sh600000, 600000.SH 等。
    """
    if not symbol:
        raise ValueError("symbol 不能为空")

    raw = symbol.strip().upper()
    raw = raw.replace("-", "").replace("_", "").replace(" ", "")

    # 形如 000001.SZ 或 000001SZ
    m = re.match(r"^(\d{6})(SH|SZ|BJ)$", raw)
    if m:
        code, ex = m.group(1), m.group(2)
        return f"{code}.{ex}"

    m = re.match(r"^(\d{6})\.(SH|SZ|BJ)$", raw)
    if m:
        code, ex = m.group(1), m.group(2)
        return f"{code}.{ex}"

    # 形如 SZ000001
    m = re.match(r"^(SH|SZ|BJ)(\d{6})$", raw)
    if m:
        ex, code = m.group(1), m.group(2)
        return f"{code}.{ex}"

    # 只有代码
    m = re.match(r"^(\d{6})$", raw)
    if m:
        code = m.group(1)
        ex = infer_exchange(code)
        return f"{code}.{ex}"

    raise ValueError(f"无法识别的 symbol: {symbol}")


def symbol_to_code(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    return normalized.split(".")[0]
