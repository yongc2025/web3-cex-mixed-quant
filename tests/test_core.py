import asyncio
import unittest
from src.config import config
from src.models import StandardizedSignal, TokenInfo, ChainType, SignalType, SecurityInfo
from src.security import SolanaSecurityChecker

class TestCoreLogic(unittest.TestCase):
    def setUp(self):
        # 模拟配置
        config.set("filters.min_liquidity", 100)
        config.set("filters.require_mint_disabled", True)

    def test_signal_model(self):
        """测试数据模型初始化"""
        token = TokenInfo(address="addr123", symbol="TEST", name="Test Token", decimals=9)
        signal = StandardizedSignal(
            id="test_id",
            chain=ChainType.SOLANA,
            token=token,
            signal_type=SignalType.NEW_POOL,
            data={"liquidity": 500.0}
        )
        self.assertEqual(signal.token.symbol, "TEST")
        self.assertEqual(signal.data["liquidity"], 500.0)

    def test_security_check_logic(self):
        """测试安全检查器的接口逻辑"""
        # 注意：SolanaSecurityChecker 的方法是 staticmethod 且是 async 的
        self.assertTrue(hasattr(SolanaSecurityChecker, 'check_mint_authority'))
        self.assertTrue(hasattr(SolanaSecurityChecker, 'check_freeze_authority'))

if __name__ == "__main__":
    unittest.main()
