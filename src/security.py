from typing import Dict, Any, Optional
from .rpc_manager import rpc_manager
import base58

class SolanaSecurityChecker:
    """
    专家级 Solana 代币安全检查器
    专门针对土狗项目的权限 (Mint/Freeze) 和流动性 (LP) 进行深度扫描
    """
    
    @staticmethod
    async def check_mint_authority(token_address: str) -> bool:
        """
        检查 Mint 权限是否已丢弃 (Renounced)
        """
        # 调用 getAccountInfo
        params = [token_address, {"encoding": "jsonParsed"}]
        result = await rpc_manager.call_with_retry("getAccountInfo", params)
        
        if result and "value" in result and result["value"]:
            data = result["value"].get("data", {})
            if isinstance(data, dict) and data.get("program") == "spl-token":
                mint_info = data.get("parsed", {}).get("info", {})
                # 如果 mintAuthority 为 null，说明权限已丢弃
                return mint_info.get("mintAuthority") is None
        return False

    @staticmethod
    async def check_freeze_authority(token_address: str) -> bool:
        """
        检查 Freeze 权限是否已丢弃
        """
        params = [token_address, {"encoding": "jsonParsed"}]
        result = await rpc_manager.call_with_retry("getAccountInfo", params)
        
        if result and "value" in result and result["value"]:
            data = result["value"].get("data", {})
            if isinstance(data, dict) and data.get("program") == "spl-token":
                mint_info = data.get("parsed", {}).get("info", {})
                return mint_info.get("freezeAuthority") is None
        return False

    @staticmethod
    async def check_lp_burned(pool_id: str) -> bool:
        """
        检查 LP Token 是否已销毁 (Burned)
        原理：查看 LP 代币的 Holder，是否 99%+ 在黑洞地址
        """
        # 注意：此项检查需要先定位 LP Mint 地址，在免费节点上较为复杂
        # 简单实现：通过 getLargestAccounts 查看持有者
        # 实际生产中通常监听 Token Burn 事件或查询 Burn 地址余额
        return False # 初始设为 False，待进一步解析 LP 结构

    async def get_full_security_report(self, token_address: str, pool_id: Optional[str] = None) -> Dict[str, bool]:
        """汇总安全报告"""
        mint_revoked = await self.check_mint_authority(token_address)
        freeze_revoked = await self.check_freeze_authority(token_address)
        
        return {
            "mint_revoked": mint_revoked,
            "freeze_revoked": freeze_revoked,
            "lp_burned": False # 待增强
        }
