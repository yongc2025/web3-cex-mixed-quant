import asyncio
import json
import aiohttp
from typing import Optional
from .interfaces import IWatcher
from .models import StandardizedSignal, ChainType, SignalType, TokenInfo, SecurityInfo
from .config import config

from .rpc_manager import rpc_manager
from .security import SolanaSecurityChecker


class SolanaRaydiumWatcher(IWatcher):
    """
    基于免费 WSS 节点的 Solana/Raydium 监听器
    重构：WSS 只负责收签名 → 丢队列 → worker 并发处理，不阻塞事件循环
    """
    RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    WSOL_ADDRESS = "So11111111111111111111111111111111111111112"

    def __init__(self, engine=None, db=None, notifiers=None):
        self.is_running = False
        self.engine = engine
        self.db = db
        self.notifiers = notifiers or []
        self.security_checker = SolanaSecurityChecker()

        # 信号队列：WSS 收到的签名先排队，worker 按并发度消费
        self._signal_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        # 通知队列：过滤通过的信号排队推送，不阻塞处理链
        self._notify_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        # 并发控制：同时最多处理 3 个信号（避免 RPC 风暴）
        self._semaphore = asyncio.Semaphore(3)

    async def start(self):
        """启动所有后台任务"""
        self.is_running = True
        asyncio.create_task(self._listen_loop())
        asyncio.create_task(self._signal_worker())
        asyncio.create_task(self._notify_worker())
        print("[INFO] SolanaRaydiumWatcher 已启动（WSS + SignalWorker + NotifyWorker）")

    async def stop(self):
        self.is_running = False
        print("[INFO] SolanaRaydiumWatcher 已停止")

    # ─── 第一层：WSS 只管收签名，不做任何处理 ───

    async def _listen_loop(self):
        """WSS 监听：只收签名，丢进队列"""
        wss_endpoints = config.get("solana.wss_endpoints", ["wss://api.mainnet-beta.solana.com"])
        proxy = config.get("app.proxy")
        current_wss = wss_endpoints[0]

        while self.is_running:
            try:
                print(f"[DEBUG] 正在连接 WSS: {current_wss} (代理: {proxy if proxy else '无'})")

                connector = None
                if proxy:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy)

                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.ws_connect(current_wss, heartbeat=20) as websocket:
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
                                    # 只丢队列，不处理，绝不阻塞
                                    if self._signal_queue.full():
                                        print(f"[WARN] 信号队列已满，丢弃: {signature[:16]}...")
                                        continue
                                    self._signal_queue.put_nowait(signature)
                            elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                print(f"[ERROR] WSS 监听中断: {e}，5秒后尝试重连...")
                await asyncio.sleep(5)

    # ─── 第二层：Worker 按并发度消费队列 ───

    async def _signal_worker(self):
        """从队列取签名，限流处理"""
        while self.is_running:
            try:
                signature = await self._signal_queue.get()
                # 用信号量控制并发，避免同时打爆 RPC
                asyncio.create_task(self._process_with_semaphore(signature))
            except Exception as e:
                print(f"[ERROR] SignalWorker 异常: {e}")

    async def _process_with_semaphore(self, signature: str):
        """带信号量的处理包装"""
        async with self._semaphore:
            await self._handle_new_pool(signature)

    async def _handle_new_pool(self, signature: str):
        """深度解析事务：过滤通过后丢通知队列"""
        print(f"[DEBUG] 处理新池信号: {signature[:16]}...")

        await asyncio.sleep(2)

        tx_data = await rpc_manager.call_with_retry(
            "getTransaction",
            [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        )

        if not tx_data:
            print(f"[SKIP] RPC 返回空数据: {signature[:16]}")
            return

        account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
        if len(account_keys) < 10:
            print(f"[SKIP] accountKeys 不足 10 个 ({len(account_keys)}): {signature[:16]}")
            return

        token_address = ""
        for key in account_keys:
            if key != self.WSOL_ADDRESS and key not in [self.RAYDIUM_LP_V4, "11111111111111111111111111111111"]:
                token_address = key
                break

        if not token_address:
            print(f"[SKIP] 未找到目标代币: {signature[:16]}")
            return

        print(f"[INFO] 发现代币: {token_address[:16]}... 开始审计")

        security_report = await self.security_checker.get_full_security_report(token_address)

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

        if self.engine and not await self.engine.run(signal):
            print(f"[FILTER] 信号被过滤: {token_address[:16]}")
            return

        # 过滤通过 → 丢通知队列，不在这里直接发
        print(f"[NOTIFY] 信号通过过滤，排队推送: {token_address[:16]}")
        if self.db:
            await self.db.save_signal(signal)
        if self._notify_queue.full():
            print(f"[WARN] 通知队列已满，丢弃信号: {token_address[:16]}")
            return
        self._notify_queue.put_nowait(signal)

    # ─── 第三层：通知 Worker，限流推送 ───

    async def _notify_worker(self):
        """消费通知队列，限流发送，绝不能阻塞信号处理"""
        while self.is_running:
            try:
                signal = await self._notify_queue.get()
                for notifier in self.notifiers:
                    try:
                        await asyncio.wait_for(notifier.notify(signal), timeout=10)
                    except asyncio.TimeoutError:
                        print(f"[WARN] 通知超时: {type(notifier).__name__}")
                    except Exception as e:
                        print(f"[ERROR] 通知失败 ({type(notifier).__name__}): {e}")
                print(f"[DONE] 推送完成: {signal.token.address[:16]}...")
                # 限流：每次推送间隔 0.5 秒，避免 Discord rate limit
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[ERROR] NotifyWorker 异常: {e}")
