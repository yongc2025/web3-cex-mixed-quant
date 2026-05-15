# 技术方案设计 — docs/DESIGN.md

## 1. 架构总览
系统采用 **插件化监听 + 统一信号处理 + 多端路由推送** 的架构模式。

### 核心组件
- **Chain Watcher (监听层)**: 针对不同链（当前优先 Solana）的 RPC/WSS 监听。
- **Signal Engine (处理层)**: 核心筛选逻辑，支持多维度过滤。
- **Store Manager (存储层)**: 针对“土狗”项目生命周期短的特点，采用混合存储方案。
- **Dispatcher (路由层)**: 将处理好的信号根据配置分发至 WeCom、Discord。
- **Bot Interface (交互层)**: Discord 指令响应。

## 2. 技术栈选型
- **语言**: Python 3.10+ (量化生态成熟)
- **底层库**: `solders` (Solana SDK), `base58`
- **数据库**: **SQLite + JSONB** (轻量级满足初期需求，通过 JSONB 保持 schema 灵活性以便未来迁移 PostgreSQL)
- **通信**: `discord.py` (异步交互), `httpx` (Webhook 推送)

## 3. 关键数据结构设计

### 信号对象 (Signal)
```json
{
  "id": "uuid",
  "chain": "solana",
  "token": {
    "address": "...",
    "symbol": "...",
    "decimals": 9,
    "security": { "mint_revoked": true, "freeze_revoked": true }
  },
  "event": "new_pool / large_buy",
  "data": { "liquidity": 10000, "dex": "Raydium" },
  "timestamp": 1625097600
}
```

## 4. 专家建议方案 (Vibe Logic)
作为资深专家，针对“土狗”场景，系统的核心竞争力在于 **“去伪存真”**：
1. **多级过滤**: 
   - P0 (安全级): 检查 Mint Authority, Freeze Authority, LP Burn 状态。
   - P1 (热度级): 推送前检查是否有 Telegram 链接及 Twitter 活跃。
2. **轻量化原则**: 
   - 考虑到 Solana 每日新盘上万，仅存储 **通过 P0 过滤** 的项目，避免垃圾数据撑爆 SQLite。
   - 信号推送结果保留 7 天，过期自动清理。

## 5. 模块划分
- `src/watchers/`: 存放各链监听脚本。
- `src/processors/` : 存放核心过滤逻辑插件。
- `src/notifiers/`: 存放 WeCom/Discord 推送逻辑。
- `src/db/`: 数据库初始化与常用查询。

## 6. 确认项
- 是否同意使用 **SQLite** 作为初始存储？
- 推送延迟目标是否设定为 **< 2s** (基于公共 RPC 现状)？
