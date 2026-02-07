from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
from typing import Optional

import pandas as pd


def _hash_key(key: str) -> str:
    return hashlib.md5(key.encode("utf-8")).hexdigest()


@dataclass
class CacheStore:
    base_dir: Path

    def path_for(self, key: str) -> Path:
        safe = _hash_key(key)
        return self.base_dir / f"{safe}.csv"

    def load(self, key: str) -> Optional[pd.DataFrame]:
        path = self.path_for(key)
        if not path.exists():
            return None
        return pd.read_csv(path)

    def save(self, key: str, df: pd.DataFrame) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(key)
        df.to_csv(path, index=False)
        return path
