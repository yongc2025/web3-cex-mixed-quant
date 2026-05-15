import httpx
import asyncio
from typing import List, Optional, Dict, Any
from .config import config


class RPCManager:
    """
    RPC 节点管理器：优先用付费节点，失败自动降级到公共节点
    """
    def __init__(self):
        self.nodes: List[str] = []
        self._initialized = False
        self._current_idx = 0

    def _ensure_loaded(self):
        if self._initialized:
            return
        raw = config.get("solana.rpc_endpoints") or config.get("rpc.nodes") or [
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana"
        ]
        # 付费节点排前面，公共节点排后面
        paid = [n for n in raw if "helius" in n or "quicknode" in n or "alchemy" in n]
        free = [n for n in raw if n not in paid]
        self.nodes = paid + free
        self._initialized = True
        print(f"[INFO] RPC 节点已加载: {len(self.nodes)} 个")
        for i, n in enumerate(self.nodes):
            tag = "💰 付费" if i < len(paid) else "🆓 免费"
            print(f"  [{i+1}] {tag}: {n[:60]}...")

    def _get_node(self) -> str:
        """顺序取节点：先用第一个（Helius），失败了切下一个"""
        self._ensure_loaded()
        node = self.nodes[self._current_idx % len(self.nodes)]
        return node

    def _rotate(self):
        """切到下一个节点"""
        self._current_idx += 1
        if self._current_idx >= len(self.nodes):
            self._current_idx = 0  # 全部失败就回到 Helius 重试
        print(f"[RPC] 切换到节点 [{self._current_idx + 1}]: {self._get_node()[:50]}...")

    async def call_with_retry(self, method: str, params: List[Any], max_retries: int = 4) -> Optional[Dict[str, Any]]:
        self._ensure_loaded()

        for i in range(max_retries):
            node_url = self._get_node()
            payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            try:
                proxy = config.get("app.proxy")
                async with httpx.AsyncClient(timeout=10.0, proxy=proxy) as client:
                    response = await client.post(node_url, json=payload)
                    if response.status_code == 200:
                        res_json = response.json()
                        if "result" in res_json:
                            if i > 0:
                                print(f"[RPC] ✅ 请求成功: {node_url[:50]} (重试 {i} 次)")
                            return res_json["result"]
                        elif "error" in res_json:
                            err_msg = res_json["error"].get("message", "unknown")
                            print(f"[RPC] ❌ {node_url[:40]}: {err_msg}")
                    elif response.status_code == 403:
                        print(f"[RPC] 🚫 被拒绝: {node_url[:40]}")
                    elif response.status_code == 429:
                        print(f"[RPC] ⏳ 限流: {node_url[:40]}")
                    else:
                        print(f"[RPC] ❓ HTTP {response.status_code}: {node_url[:40]}")
            except Exception as e:
                print(f"[RPC] 💥 连接失败 ({node_url[:40]}): {e}")

            # 失败了，切下一个节点
            self._rotate()
            await asyncio.sleep(0.5)

        print(f"[RPC] ⚠️ 所有节点都失败，放弃: {method}")
        return None


rpc_manager = RPCManager()
