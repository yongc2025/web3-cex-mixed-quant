import asyncio
import json
import aiohttp
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

        while self.is_running:
            try:
                print(f"[DEBUG] 正在连接 WSS: {current_wss} (代理: {proxy if proxy else '无'})")
                
                # aiohttp WebSocket，复用 ProxyConnector
                connector = None
                if proxy:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy)
                
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.ws_connect(
                        current_wss,
                        heartbeat=20
                    ) as websocket:
                        subscribe_msg = {
                            "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                            "params": [
                                {"mentions": [self.RAYDIUM_LP_V4]},
                                {"commitment": "finalized"}
                            ]
                        }
                        await websocket.send_json(subscribe_msg)
                        print(f"[INFO] 成功订阅 Raydium 信号于 {current_wss}")
                        
                        async for message in websocket:
                            if message.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(message.data)
                                signature = data.get("params", {}).get("result", {}).get("value", {}).get("signature")
                                if signature:
                                    asyncio.create_task(self._handle_new_pool(signature))
                            elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                print(f"[ERROR] WSS 监听中断: {e}，5秒后尝试重连...")
                await asyncio.sleep(5)

    async def _handle_new_pool(self, signature: str):
        """
        深度解析事务并串联过滤、存储与推送
        """
        print(f"[DEBUG] 处理新池信号: {signature[:16]}...")
        
        await asyncio.sleep(2)
        
        tx_data = await rpc_manager.call_with_retry(
            "getTransaction", 
            [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        )

        if not tx_data:
            print(f"[SKIP] RPC 返回空数据: {signature[:16]}")
            return

        # 资深专家逻辑：从交易指令中提取代币地址
        account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
        if len(account_keys) < 10:
            print(f"[SKIP] accountKeys 不足 10 个 ({len(account_keys)}): {signature[:16]}")
            return

        # 简单启发式搜索：寻找非 WSOL 的代币地址作为目标
        token_address = ""
        for key in account_keys:
            if key != self.WSOL_ADDRESS and key not in [self.RAYDIUM_LP_V4, "11111111111111111111111111111111"]:
                token_address = key
                break
        
        if not token_address:
            print(f"[SKIP] 未找到目标代币: {signature[:16]}")
            return

        print(f"[INFO] 发现代币: {token_address[:16]}... 开始审计")

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
            print(f"[FILTER] 信号被过滤: {token_address[:16]}")
            return

        # 4. 存储与推送
        print(f"[NOTIFY] 正在推送信号: {token_address[:16]}")
        if self.db: await self.db.save_signal(signal)
        for notifier in self.notifiers:
            await notifier.notify(signal)
        print(f"[DONE] 推送完成: {token_address[:16]}")
