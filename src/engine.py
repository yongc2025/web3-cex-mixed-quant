from typing import List
from .interfaces import IProcessor
from .models import StandardizedSignal
from .config import config

class SecurityFilter(IProcessor):
    """
    第一级过滤：核心安全过滤 (Stateless)
    """
    async def process(self, signal: StandardizedSignal) -> bool:
        if config.get("filters.require_mint_disabled") and not signal.security.mint_revoked:
            return False
        if config.get("filters.require_lp_burned") and not signal.security.lp_burned:
            return False
        return True

class LiquidityFilter(IProcessor):
    """
    第二级过滤：流动性过滤 (Stateless)
    """
    async def process(self, signal: StandardizedSignal) -> bool:
        min_liq = config.get("filters.min_liquidity", 0)
        current_liq = signal.data.get("liquidity", 0)
        return current_liq >= min_liq

class FilterEngine:
    """
    过滤引擎：组合多个处理器
    """
    def __init__(self):
        self.processors: List[IProcessor] = [
            SecurityFilter(),
            LiquidityFilter()
        ]

    async def run(self, signal: StandardizedSignal) -> bool:
        for processor in self.processors:
            if not await processor.process(signal):
                return False
        return True
