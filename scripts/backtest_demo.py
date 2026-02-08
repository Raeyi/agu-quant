from pathlib import Path
import sys
from datetime import date

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.backtest import backtest_multi_positions
from agu_quant.data import AkShareClient
from agu_quant.features import compute_sentiment_daily
from agu_quant.reporting import report_from_multi


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True)
    symbols = ["000001.SZ", "600000.SH", "000333.SZ", "600519.SH"]
    bars_by_symbol = {}
    positions_by_symbol = {}

    # 超短线：最近 N 个交易日 + 情绪（涨停）信号
    lookback_days = 60
    hold_days = 2
    end_date = date.today().strftime("%Y-%m-%d")
    start_date = "2024-01-01"

    for s in symbols:
        bars = client.daily_bars(s, start=start_date, end=end_date)
        bars = bars.sort_values("date").copy()
        if len(bars) > lookback_days:
            bars = bars.tail(lookback_days).copy()

        # 情绪代理：前一日接近涨停（>= 9.5%）
        pct = bars["pct_chg"].fillna(0.0)
        signal = (pct.shift(1) >= 0.095).astype(float)

        # 持有 1-2 天
        pos = signal.copy()
        for i in range(1, hold_days):
            pos = (pos + signal.shift(i).fillna(0.0)).clip(0.0, 1.0)

        pos.index = bars["date"]
        bars_by_symbol[s] = bars
        positions_by_symbol[s] = pos

    # 计算情绪指标：全市场版本（较慢）
    # 如网络不稳定，可设置为 False 或降低 max_symbols
    full_market_sentiment = True
    max_symbols = 300
    sleep_sec = 0.2
    sentiment = pd.DataFrame()
    if full_market_sentiment:
        stock_list = client.stock_list()
        symbols_all = stock_list["symbol"].tolist()[:max_symbols]
        # 根据样本日期窗口限定拉取区间，避免过大
        if bars_by_symbol:
            dates = pd.concat([b["date"] for b in bars_by_symbol.values() if not b.empty])
            if not dates.empty:
                start_date = pd.to_datetime(dates.min()).strftime("%Y-%m-%d")
                end_date = pd.to_datetime(dates.max()).strftime("%Y-%m-%d")
        bars_all = {}
        for s in symbols_all:
            try:
                bars = client.daily_bars(s, start=start_date, end=end_date)
                if bars is None or bars.empty:
                    continue
                bars_all[s] = bars
                if sleep_sec > 0:
                    import time

                    time.sleep(sleep_sec)
            except Exception:
                continue
        sentiment = compute_sentiment_daily(bars_all)
    else:
        # 样本情绪（基于当前 symbols）
        sentiment = compute_sentiment_daily(bars_by_symbol)
    sentiment = sentiment.set_index("date")

    weights = {
        "000001.SZ": 0.25,
        "600000.SH": 0.25,
        "000333.SZ": 0.25,
        "600519.SH": 0.25,
    }

    # 示例：动态权重（短期强势 => 1，否则 0）
    weights_by_symbol = {}
    for s, bars in bars_by_symbol.items():
        bars = bars.sort_values("date").copy()
        mom_3d = bars["close"].pct_change(3).fillna(0.0)
        w = (mom_3d > 0).astype(float)
        w.index = bars["date"]
        weights_by_symbol[s] = w

    # 情绪过滤：仅在情绪较强时持仓（样本内近似）
    if not sentiment.empty:
        ok_days = (sentiment["limit_up_ratio"] >= 0.25) | (sentiment["max_consecutive"] >= 1)
        for s, pos in positions_by_symbol.items():
            pos = pos.copy()
            pos.loc[~ok_days.reindex(pos.index).fillna(False)] = 0.0
            positions_by_symbol[s] = pos

    result = backtest_multi_positions(
        bars_by_symbol=bars_by_symbol,
        positions_by_symbol=positions_by_symbol,
        commission_bps=1.0,
        slippage_bps=1.0,
        stamp_tax_bps=10.0,
        transfer_fee_bps=0.0,
        weights=weights,
        weights_by_symbol=weights_by_symbol,
    )

    out_dir = Path("data/reports")
    report = report_from_multi(result)
    report.save(out_dir, prefix="backtest_demo")

    if not sentiment.empty:
        sentiment_out = out_dir / "backtest_demo_sentiment.csv"
        sentiment.reset_index().to_csv(sentiment_out, index=False)

    # 输出股票名称版本（用于展示）
    stock_list = client.stock_list()
    name_map = dict(zip(stock_list["symbol"], stock_list["name"]))
    equity = result.equity_curve.copy()
    rename_cols = {}
    for c in equity.columns:
        if c.startswith("net_ret_"):
            symbol = c.replace("net_ret_", "")
            rename_cols[c] = f"net_ret_{name_map.get(symbol, symbol)}"
    equity = equity.rename(columns=rename_cols)
    equity_out = out_dir / "backtest_demo_equity_names.csv"
    equity.to_csv(equity_out, index=False)

    pd.set_option("display.max_columns", None)
    print(result.equity_curve.tail(5))
    print(result.metrics)
    print(f"已输出: {out_dir}")


if __name__ == "__main__":
    main()
