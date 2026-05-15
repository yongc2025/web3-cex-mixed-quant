from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
import time

class ChainType(Enum):
    SOLANA = "solana"
    ETH = "ethereum"
    BASE = "base"

class SignalType(Enum):
    NEW_POOL = "new_pool"
    LARGE_BUY = "large_buy"
    WHALE_MOVE = "whale_movement"
    SECURITY_ALERT = "security_alert"

@dataclass
class TokenInfo:
    address: str
    symbol: str
    decimals: int
    name: Optional[str] = None
    
@dataclass
class SecurityInfo:
    mint_revoked: bool = False
    freeze_revoked: bool = False
    lp_burned: bool = False
    top_holders_percent: float = 0.0

@dataclass
class StandardizedSignal:
    id: str
    chain: ChainType
    token: TokenInfo
    signal_type: SignalType
    data: Dict[str, Any]
    security: SecurityInfo = field(default_factory=SecurityInfo)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain": self.chain.value,
            "token": {
                "address": self.token.address,
                "symbol": self.token.symbol,
                "name": self.token.name
            },
            "signal_type": self.signal_type.value,
            "data": self.data,
            "security": {
                "mint_revoked": self.security.mint_revoked,
                "freeze_revoked": self.security.freeze_revoked,
                "lp_burned": self.security.lp_burned
            },
            "timestamp": self.timestamp
        }
