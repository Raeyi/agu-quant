from pathlib import Path
import sys
import time

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient
from agu_quant.features import (
    compute_theme_panel,
    identify_main_theme,
    compute_theme_rotation,
    rank_themes,
)


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True, verbose=True)

    symbols = ["000001.SZ", "000002.SZ", "600000.SH", "600519.SH"]
    # 概念映射：从 AkShare 获取真实概念板块
    symbol_to_theme = {}
    concept_list = client.concept_list_em(allow_cache_fallback=True)
    if concept_list is None or concept_list.empty:
        print("概念列表为空，使用空映射继续演示。")
    else:
        # 控制请求量，优先覆盖样本股票
        concept_names = concept_list["concept"].tolist()
        max_concepts = 50
        for concept in concept_names:
            if len(symbol_to_theme) >= len(symbols):
                break
            if max_concepts <= 0:
                break
            try:
                cons = client.concept_constituents_em(concept)
            except Exception as exc:
                print(f"{concept} 成分获取失败: {exc}")
                continue
            if cons is None or cons.empty:
                continue
            for symbol in cons["symbol"].tolist():
                if symbol not in symbol_to_theme:
                    symbol_to_theme[symbol] = concept
            max_concepts -= 1
            time.sleep(0.2)

    bars_by_symbol = {}
    for symbol in symbols:
        try:
            bars = client.daily_bars(
                symbol,
                start="2024-01-01",
                end="2024-06-30",
                adjust="qfq",
                timeout=15,
            )
            bars_by_symbol[symbol] = bars
        except Exception as exc:
            print(f"{symbol} 拉取失败: {exc}")

    # 对示例股票做概念映射缺省处理
    for symbol in symbols:
        symbol_to_theme.setdefault(symbol, "未分类")

    panel = compute_theme_panel(bars_by_symbol, symbol_to_theme)
    if panel is None or panel.empty:
        print("题材面板为空，可能是数据未获取到。")
        return

    print("题材面板（最近 5 行）:")
    print(panel.tail(5))

    last_date = panel["date"].max()
    ranking = rank_themes(panel, date=last_date, top_n=5)
    print(f"题材排行（{last_date}）:")
    print(ranking)

    main_theme = identify_main_theme(panel, top_k=1)
    rotation = compute_theme_rotation(main_theme)
    print("主线题材:")
    print(main_theme.tail(5))
    print("题材轮动:")
    print(rotation.tail(5))


if __name__ == "__main__":
    main()
