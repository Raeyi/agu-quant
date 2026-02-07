from pathlib import Path
import sys

# Allow running from repo root without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agu_quant.data import AkShareClient


def main() -> None:
    client = AkShareClient(cache_dir=Path("data/cache"), use_cache=True)
    try:
        daily = client.daily_bars(
            "000001.SZ",
            start="2024-01-01",
            end="2024-06-30",
            timeout=15,
        )
        print(daily.tail(5))
    except Exception as exc:
        print(f"拉取失败: {exc}")
        print("建议: 检查网络/代理设置，或稍后重试。")
        print("如已开启代理，可设置系统环境变量 HTTP_PROXY / HTTPS_PROXY。")


if __name__ == "__main__":
    main()
