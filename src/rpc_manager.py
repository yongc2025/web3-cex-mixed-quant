import httpx
import asyncio
import time
from typing import List, Optional, Dict, Any
from .config import config


class RPCManager:
    """
    RPC 节点管理器：付费优先 → 失败冷却 → 自动降级
    """
    COOLDOWN_SECONDS = 30

    def __init__(self):
        self.nodes: List[str] = []
        self._initialized = False
        self._cooldown: Dict[str, float] = {}

    def _ensure_loaded(self):
        if self._initialized:
            return
        raw = config.get("solana.rpc_endpoints") or config.get("rpc.nodes") or [
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana"
        ]
        paid = [n for n in raw if "helius" in n or "quicknode" in n or "alchemy" in n]
        free = [n for n in raw if n not in paid]
        self.nodes = paid + free
        self._initialized = True
        print(f"[INFO] RPC 节点已加载: {len(self.nodes)} 个")
        for i, n in enumerate(self.nodes):
            tag = "💰" if i < len(paid) else "🆓"
            print(f"  [{i+1}] {tag} {n[:60]}...")

    def _mark_failed(self, node: str):
        self._cooldown[node] = time.time()

    def _is_cooling(self, node: str) -> bool:
        if node not in self._cooldown:
            return False
        if time.time() - self._cooldown[node] > self.COOLDOWN_SECONDS:
            del self._cooldown[node]
            return False
        return True

    def _pick_node(self) -> str:
        self._ensure_loaded()
        for node in self.nodes:
            if not self._is_cooling(node):
                return node
        return self.nodes[0]

    async def call_with_retry(self, method: str, params: List[Any], max_retries: int = 4) -> Optional[Dict[str, Any]]:
        self._ensure_loaded()

        for i in range(max_retries):
            node_url = self._pick_node()
            payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            try:
                proxy = config.get("app.proxy")
                async with httpx.AsyncClient(timeout=10.0, proxy=proxy) as client:
                    response = await client.post(node_url, json=payload)
                    if response.status_code == 200:
                        res_json = response.json()
                        if "result" in res_json:
                            return res_json["result"]
                        elif "error" in res_json:
                            print(f"[RPC] ❌ {node_url[:40]}: {res_json['error'].get('message', '')}")
                    elif response.status_code == 403:
                        print(f"[RPC] 🚫 被拒绝: {node_url[:40]}")
                        self._mark_failed(node_url)
                    elif response.status_code == 429:
                        print(f"[RPC] ⏳ 限流: {node_url[:40]}")
                        self._mark_failed(node_url)
                    else:
                        print(f"[RPC] ❓ HTTP {response.status_code}: {node_url[:40]}")
            except httpx.ConnectError as e:
                print(f"[RPC] 💥 连接拒绝: {node_url[:40]}: {e}")
                self._mark_failed(node_url)
            except httpx.TimeoutException:
                print(f"[RPC] ⏰ 超时: {node_url[:40]}")
                self._mark_failed(node_url)
            except httpx.ProxyError as e:
                print(f"[RPC] 🔒 代理错误: {node_url[:40]}: {e}")
                self._mark_failed(node_url)
            except Exception as e:
                print(f"[RPC] 💥 {type(e).__name__}: {node_url[:40]}: {e}")
                self._mark_failed(node_url)

            await asyncio.sleep(0.3)

        print(f"[RPC] ⚠️ 全部失败: {method}")
        return None


rpc_manager = RPCManager()
