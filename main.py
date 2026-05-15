import asyncio
from src.config import config
from src.db import DatabaseManager
from src.engine import FilterEngine
from src.notifiers import WeComNotifier, DiscordBotNotifier
from src.watchers import SolanaRaydiumWatcher

class AppContext:
    """
    全量上下文容器：管理所有组件的生命周期
    """
    def __init__(self):
        # 显式先加载一次配置
        config.load()
        self.db = DatabaseManager()
        self.engine = FilterEngine()
        self.wecom = WeComNotifier()
        self.discord = DiscordBotNotifier()
        self.watchers = []

    async def initialize(self):
        # 1. 确保配置已加载
        config.load()
        print(f"[DEBUG] AppContext 加载配置，Token 长度: {len(config.get('notifiers.discord_token', ''))}")
        
        # 2. 初始化数据库
        await self.db.init_db()
        
        # 3. 初始化监听器 (支持多链扩展)
        # 专家建议：通过配置动态加载监听链
        enabled_chains = config.get("app.enabled_chains", ["solana"])
        
        if "solana" in enabled_chains:
            sol_watcher = SolanaRaydiumWatcher(
                engine=self.engine, 
                db=self.db, 
                notifiers=[self.wecom, self.discord]
            )
            self.watchers.append(sol_watcher)

    async def run(self):
        # 启动所有后台任务
        tasks = []
        
        # 启动 Discord 机器人交互
        print(f"[DEBUG] 检查 Discord Token: {self.discord.token[:10]}...")
        if self.discord.token:
            print("[INFO] 正在启动 Discord Bot 异步任务...")
            tasks.append(self.discord.start_bot())
            
        # 启动各链监听器
        for watcher in self.watchers:
            tasks.append(watcher.start())
            
        print(f"[INFO] 正在并行运行 {len(tasks)} 个核心任务...")
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    app = AppContext()
    async def start_app():
        # 显式加载配置
        config.load()
        await app.initialize()
        await app.run()
        
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        print("\n[INFO] 用户手动停止系统。")
