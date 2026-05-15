import asyncio
import json
import time
import aiohttp
from typing import Optional, Set, Dict
from .interfaces import IWatcher
from .models import StandardizedSignal, ChainType, SignalType, TokenInfo, SecurityInfo
from .config import config

from .rpc_manager import rpc_manager
from .security import SolanaSecurityChecker


class SolanaRaydiumWatcher(IWatcher):
    """
    Solana/Raydium 新池监听器
    WSS → 去重 → 队列 → Worker 处理 → 通知队列 → 推送
    """
    RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    RAYDIUM_AUTHORITY = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
    WSOL_ADDRESS = "So11111111111111111111111111111111111111112"
    SYSTEM_PROGRAM = "11111111111111111111111111111111"
    TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

    def __init__(self, engine=None, db=None, notifiers=None):
        self.is_running = False
        self.engine = engine
        self.db = db
        self.notifiers = notifiers or []
        self.security_checker = SolanaSecurityChecker()

        # 信号队列
        self._signal_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        # 通知队列
        self._notify_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        # 并发控制
        self._semaphore = asyncio.Semaphore(3)
        # 去重：签名 + 代币地址，TTL 5 分钟
        self._seen_sigs: Dict[str, float] = {}
        self._seen_tokens: Dict[str, float] = {}
        self._dedup_ttl = 300  # 5 分钟

    async def start(self):
        self.is_running = True
        asyncio.create_task(self._listen_loop())
        asyncio.create_task(self._signal_worker())
        asyncio.create_task(self._notify_worker())
        asyncio.create_task(self._cleanup_seen())
        print("[INFO] SolanaRaydiumWatcher 已启动（WSS + SignalWorker + NotifyWorker）")

    async def stop(self):
        self.is_running = False
        print("[INFO] SolanaRaydiumWatcher 已停止")

    # ─── 去重清理 ───

    async def _cleanup_seen(self):
        """定期清理过期的去重记录"""
        while self.is_running:
            await asyncio.sleep(60)
            now = time.time()
            self._seen_sigs = {k: v for k, v in self._seen_sigs.items() if now - v < self._dedup_ttl}
            self._seen_tokens = {k: v for k, v in self._seen_tokens.items() if now - v < self._dedup_ttl}

    def _is_duplicate_sig(self, sig: str) -> bool:
        if sig in self._seen_sigs:
            return True
        self._seen_sigs[sig] = time.time()
        return False

    def _is_duplicate_token(self, token: str) -> bool:
        if token in self._seen_tokens:
            return True
        self._seen_tokens[token] = time.time()
        return False

    # ─── 第一层：WSS 只管收签名 ───

    async def _listen_loop(self):
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
                                if signature and not self._is_duplicate_sig(signature):
                                    if self._signal_queue.full():
                                        print(f"[WARN] 信号队列已满，丢弃: {signature[:16]}")
                                        continue
                                    self._signal_queue.put_nowait(signature)
                            elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                print(f"[ERROR] WSS 监听中断: {e}，5秒后重连...")
                await asyncio.sleep(5)

    # ─── 第二层：Worker 处理信号 ───

    async def _signal_worker(self):
        while self.is_running:
            try:
                signature = await self._signal_queue.get()
                asyncio.create_task(self._process_with_semaphore(signature))
            except Exception as e:
                print(f"[ERROR] SignalWorker 异常: {e}")

    async def _process_with_semaphore(self, signature: str):
        async with self._semaphore:
            await self._handle_new_pool(signature)

    async def _handle_new_pool(self, signature: str):
        """解析事务 → 判断是否新池 → 过滤 → 推送"""
        await asyncio.sleep(2)

        tx_data = await rpc_manager.call_with_retry(
            "getTransaction",
            [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        )

        if not tx_data:
            return

        # ── 判断是否真的是新池创建 ──
        # Raydium Initialize2 指令的特征：accountKeys 包含 LP Authority + Token Program
        account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
        if len(account_keys) < 10:
            return

        # 必须包含 Raydium Authority 才是新池创建
        if self.RAYDIUM_AUTHORITY not in account_keys:
            return

        # 必须包含 Token Program（创建代币相关）
        if self.TOKEN_PROGRAM not in account_keys:
            return

        # 提取代币地址：排除已知地址
        known = {self.WSOL_ADDRESS, self.RAYDIUM_LP_V4, self.RAYDIUM_AUTHORITY,
                 self.SYSTEM_PROGRAM, self.TOKEN_PROGRAM}
        token_address = ""
        for key in account_keys:
            if key not in known:
                token_address = key
                break

        if not token_address:
            return

        # 代币级别去重
        if self._is_duplicate_token(token_address):
            print(f"[DEDUP] 重复代币，跳过: {token_address[:16]}")
            return

        print(f"[INFO] 新池发现: {token_address[:16]}... 审计中")

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
            print(f"[FILTER] 不符合条件: {token_address[:16]}")
            return

        print(f"[NOTIFY] 推送信号: {token_address[:16]}")
        if self.db:
            await self.db.save_signal(signal)
        if self._notify_queue.full():
            print(f"[WARN] 通知队列已满，丢弃: {token_address[:16]}")
            return
        self._notify_queue.put_nowait(signal)

    # ─── 第三层：通知 Worker ───

    async def _notify_worker(self):
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
                print(f"[DONE] 推送完成: {signal.token.address[:16]}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[ERROR] NotifyWorker 异常: {e}")
