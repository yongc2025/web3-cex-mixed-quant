import asyncio
from src.config import config
from src.db import DatabaseManager
from src.engine import FilterEngine
from src.notifiers import WeComNotifier, DiscordBotNotifier
from src.watchers import SolanaRaydiumWatcher


class AppContext:
    """全量上下文容器：管理所有组件的生命周期"""
    def __init__(self):
        config.load()
        self.db = DatabaseManager()
        self.engine = FilterEngine()
        self.wecom = WeComNotifier()
        self.discord = DiscordBotNotifier()
        self.watchers = []

    async def initialize(self):
        config.load()
        print(f"[DEBUG] AppContext 加载配置，Token 长度: {len(config.get('notifiers.discord_token', ''))}")

        await self.db.init_db()

        enabled_chains = config.get("app.enabled_chains", ["solana"])

        if "solana" in enabled_chains:
            sol_watcher = SolanaRaydiumWatcher(
                engine=self.engine,
                db=self.db,
                notifiers=[self.wecom, self.discord]
            )
            self.watchers.append(sol_watcher)

    async def run(self):
        tasks = []

        # Discord Bot — 独立任务，不受 watcher 影响
        if self.discord.token:
            print("[INFO] 正在启动 Discord Bot...")
            tasks.append(self.discord.start_bot())

        # Watchers — start() 立即返回，内部 worker 自行调度
        for watcher in self.watchers:
            await watcher.start()

        print(f"[INFO] 正在并行运行 {len(tasks)} 个核心任务...")
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    app = AppContext()

    async def start_app():
        config.load()
        await app.initialize()
        await app.run()

    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        print("\n[INFO] 用户手动停止系统。")
