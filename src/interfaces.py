from abc import ABC, abstractmethod
from typing import List
from .models import StandardizedSignal

class IWatcher(ABC):
    """
    具体的链监听器接口 (如 SolanaWatcher)
    """
    @abstractmethod
    async def start(self):
        """开始监听 RPC/WSS"""
        pass

    @abstractmethod
    async def stop(self):
        """停止监听"""
        pass

class IProcessor(ABC):
    """
    信号处理/过滤引擎接口
    """
    @abstractmethod
    async def process(self, signal: StandardizedSignal) -> bool:
        """
        处理并判断信号是否满足推送条件
        """
        pass

class INotifier(ABC):
    """
    推送渠道接口 (如 Discord, WeCom)
    """
    @abstractmethod
    async def notify(self, signal: StandardizedSignal):
        """发送通知"""
        pass
