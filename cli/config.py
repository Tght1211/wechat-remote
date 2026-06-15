"""
CLI 配置管理

@author buchi
@since 2026-06-15
"""
import json
from pathlib import Path
from dataclasses import dataclass, asdict

CONFIG_FILE = Path.home() / ".wchat.json"

@dataclass
class Config:
    server_url: str = "http://localhost:9100"
    token: str = ""

    def save(self):
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))
        CONFIG_FILE.chmod(0o600)

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()
