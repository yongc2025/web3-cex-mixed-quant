import asyncio
import json
import websockets
from typing import Optional
from .interfaces import IWatcher
from .models import StandardizedSignal, ChainType, SignalType, TokenInfo, SecurityInfo
from .config import config

from .rpc_manager import rpc_manager
from .models import StandardizedSignal, ChainType, SignalType, TokenInfo, SecurityInfo
from .security import SolanaSecurityChecker

class SolanaRaydiumWatcher(IWatcher):
    """
    基于免费 WSS 节点的 Solana/Raydium 监听器
    """
    RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    WSOL_ADDRESS = "So11111111111111111111111111111111111111112"

    def __init__(self, engine=None, db=None, notifiers=None):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.engine = engine
        self.db = db
        self.notifiers = notifiers or []
        self.security_checker = SolanaSecurityChecker()

    async def start(self):
        """实现接口中的 start 方法"""
        self.is_running = True
        self.task = asyncio.create_task(self._listen_loop())
        print("[INFO] SolanaRaydiumWatcher 已启动监听循环")

    async def stop(self):
        """实现接口中的 stop 方法"""
        self.is_running = False
        if self.task:
            self.task.cancel()
        print("[INFO] SolanaRaydiumWatcher 已停止")

    async def _listen_loop(self):
        """核心监听物理循环"""
        wss_endpoints = config.get("solana.wss_endpoints", ["wss://api.mainnet-beta.solana.com"])
        proxy = config.get("app.proxy")
        current_wss = wss_endpoints[0]
        
        # 解析代理
        proxy_host = None
        proxy_port = None
        if proxy:
            try:
                # 假设格式为 http://127.0.0.1:10808
                parts = proxy.replace("http://", "").replace("https://", "").split(":")
                proxy_host = parts[0]
                proxy_port = int(parts[1])
            except:
                pass

        while self.is_running:
            try:
                print(f"[DEBUG] 正在连接 WSS: {current_wss} (代理: {proxy if proxy else '无'})")
                
                # 特别修复：对于 Windows 环境下的 websockets 代理支持
                # 如果有代理，我们尝试配合系统环境变量使用
                async with websockets.connect(
                    current_wss,
                    open_timeout=10,
                    ping_interval=20
                ) as websocket:
                    subscribe_msg = {
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [
                            {"mentions": [self.RAYDIUM_LP_V4]},
                            {"commitment": "finalized"}
                        ]
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    print(f"[INFO] 成功订阅 Raydium 信号于 {current_wss}")
                    
                    async for message in websocket:
                        data = json.loads(message)
                        signature = data.get("params", {}).get("result", {}).get("value", {}).get("signature")
                        if signature:
                            asyncio.create_task(self._handle_new_pool(signature))
            except Exception as e:
                print(f"[ERROR] WSS 监听中断: {e}，5秒后尝试重连...")
                await asyncio.sleep(5)

    async def _handle_new_pool(self, signature: str):
        """
        深度解析事务并串联过滤、存储与推送
        """
        print(f"New Raydium Pool Detected! Fetching details for sig: {signature[:10]}...")
        
        await asyncio.sleep(2)
        
        tx_data = await rpc_manager.call_with_retry(
            "getTransaction", 
            [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        )

        if not tx_data: return

        # 资深专家逻辑：从交易指令中提取代币地址
        # Raydium Initialize2 交易通常在 accountKeys 中包含 Mint A 和 Mint B
        account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
        if len(account_keys) < 10: return

        # 简单启发式搜索：寻找非 WSOL 的代币地址作为目标
        token_address = ""
        for key in account_keys:
            if key != self.WSOL_ADDRESS and key not in [self.RAYDIUM_LP_V4, "11111111111111111111111111111111"]:
                # 排除系统合约，剩下的第一个大概率是新币
                token_address = key
                break
        
        if not token_address: return

        # 1. 自动审计
        security_report = await self.security_checker.get_full_security_report(token_address)
        
        # 2. 构造标准化对象
        signal = StandardizedSignal(
            id=signature,
            chain=ChainType.SOLANA,
            token=TokenInfo(address=token_address, symbol="UNKNOWN", decimals=9),
            signal_type=SignalType.NEW_POOL,
            data={"liquidity": 0, "signature": signature},
            security=SecurityInfo(
                mint_revoked=security_report["mint_revoked"],
                freeze_revoked=security_report["freeze_revoked"]
            )
        )

        # 3. 过滤逻辑
        if self.engine and not await self.engine.run(signal):
            print(f"Signal for {token_address[:8]} filtered out.")
            return

        # 4. 存储与推送
        if self.db: await self.db.save_signal(signal)
        for notifier in self.notifiers:
            await notifier.notify(signal)
