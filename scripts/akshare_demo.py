from pathlib import Path
import sys

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient, build_quality_report


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True, verbose=True)
    try:
        adjust = "qfq"  # 可选: qfq / hfq / none
        daily = client.daily_bars(
            "000001.SZ",
            start="2024-01-01",
            end="2024-06-30",
            adjust=adjust,
            timeout=15,
        )
        print(daily.tail(5))
        report = build_quality_report(daily)
        print("质量报告:", report)
        if "adj_method" in daily.columns and not daily.empty:
            print("当前复权口径:", daily["adj_method"].iloc[-1])
        print("缓存目录:", client.cache_dir)
    except Exception as exc:
        print(f"拉取失败: {exc}")
        print("建议: 检查网络/代理设置，或稍后重试。")
        print("如已开启代理，可设置系统环境变量 HTTP_PROXY / HTTPS_PROXY。")


if __name__ == "__main__":
    main()
