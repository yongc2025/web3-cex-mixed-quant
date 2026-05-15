import httpx
import random
import asyncio
from typing import List, Optional, Dict, Any
from .config import config

class RPCManager:
    """
    专家级免费节点管理系统 (Node Rotation)
    解决免费节点 Rate Limit 痛点
    """
    def __init__(self):
        # 默认内置一些知名的公共节点，也可从 config 加载自定义列表
        self.nodes = config.get("rpc.nodes", [
            "https://api.mainnet-beta.solana.com",
            "https://solana-mainnet.g.allthatnode.com",
            "https://rpc.ankr.com/solana",
            "https://solana-api.projectserum.com"
        ])
        self.current_idx = 0

    def get_next_node(self) -> str:
        """随机或轮询获取下一个节点"""
        return random.choice(self.nodes)

    async def call_with_retry(self, method: str, params: List[Any], max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        带轮询与重试的 RPC 调用
        """
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
                async with httpx.AsyncClient(timeout=10.0, proxies=proxy) as client:
                    response = await client.post(node_url, json=payload)
                    if response.status_code == 200:
                        res_json = response.json()
                        if "result" in res_json:
                            return res_json["result"]
                        elif "error" in res_json:
                            print(f"RPC Error from {node_url}: {res_json['error'].get('message')}")
                    elif response.status_code == 429:
                        print(f"Rate limited by {node_url}, switching...")
            except Exception as e:
                print(f"Request failed to {node_url}: {str(e)}")
            
            # 如果失败，等待一个小随机间隔后换个节点重试
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        return None

rpc_manager = RPCManager()
