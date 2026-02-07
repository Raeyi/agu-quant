from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("data")
    cache_dir: Path = Path("data/cache")
    timezone: str = "Asia/Shanghai"
