import httpx
import random
import asyncio
from typing import List, Optional, Dict, Any
from .config import config


class RPCManager:
    """
    RPC 节点管理器：支持轮询 + 重试 + 自动降级
    """
    def __init__(self):
        self.nodes: List[str] = []
        self._initialized = False

    def _ensure_loaded(self):
        """延迟加载配置，确保 config.load() 已执行"""
        if self._initialized:
            return
        self.nodes = config.get("solana.rpc_endpoints") or config.get("rpc.nodes") or [
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana"
        ]
        # Helius 付费节点优先，公共节点放最后
        self.nodes.sort(key=lambda x: ("helius" not in x, "publicnode" not in x, "ankr" not in x))
        self._initialized = True
        print(f"[INFO] RPC 节点已加载: {len(self.nodes)} 个")
        for i, n in enumerate(self.nodes):
            print(f"  [{i+1}] {n[:60]}...")

    def get_next_node(self) -> str:
        self._ensure_loaded()
        # 优先用第一个（Helius），失败时随机切
        return random.choice(self.nodes)

    def mark_failed(self, node_url: str):
        """标记节点失败，可以实现更智能的策略"""
        pass

    async def call_with_retry(self, method: str, params: List[Any], max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """带轮询与重试的 RPC 调用"""
        self._ensure_loaded()

        for i in range(max_retries):
            node_url = self.get_next_node()
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            try:
                proxy = config.get("app.proxy")
                async with httpx.AsyncClient(timeout=10.0, proxy=proxy) as client:
                    response = await client.post(node_url, json=payload)
                    if response.status_code == 200:
                        res_json = response.json()
                        if "result" in res_json:
                            return res_json["result"]
                        elif "error" in res_json:
                            print(f"[RPC] Error from {node_url[:40]}: {res_json['error'].get('message')}")
                    elif response.status_code == 429:
                        print(f"[RPC] Rate limited: {node_url[:40]}，切换节点...")
                    else:
                        print(f"[RPC] HTTP {response.status_code} from {node_url[:40]}")
            except Exception as e:
                print(f"[RPC] 请求失败 ({node_url[:40]}): {e}")

            await asyncio.sleep(random.uniform(0.5, 1.5))

        return None


rpc_manager = RPCManager()
