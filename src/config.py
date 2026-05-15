import yaml
import os
from typing import Any, Dict

class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def load(self, path: str = "config.yaml"):
        if not os.path.exists(path):
            self._create_default(path)
        
        with open(path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any):
        """动态设置配置并保存"""
        keys = key.split(".")
        val = self._config
        for k in keys[:-1]:
            val = val.setdefault(k, {})
        val[keys[-1]] = value
        
        # 实时持久化回 config.yaml
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(self._config, f)

    def _create_default(self, path: str):
        default_conf = {
            "app": {"debug": True},
            "filters": {
                "min_liquidity": 5000,
                "require_mint_disabled": True,
                "require_lp_burned": True
            },
            "notifiers": {
                "wecom": {"webhook_url": ""},
                "discord": {"bot_token": "", "channel_id": ""}
            },
            "rpc": {
                "solana": "https://api.mainnet-beta.solana.com"
            }
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_conf, f)

config = ConfigManager()
