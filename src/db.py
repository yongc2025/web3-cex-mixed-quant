import aiosqlite
import json
import os
from typing import List, Optional
from .models import StandardizedSignal

class DatabaseManager:
    def __init__(self, db_path: str = "data/signals.db"):
        self.db_path = db_path
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def init_db(self):
        """初始化数据库表结构并启用 WAL 模式"""
        async with aiosqlite.connect(self.db_path) as db:
            # 启用 WAL 模式提高并发性能
            await db.execute("PRAGMA journal_mode=WAL")
            
            # 信号表 (使用 JSONB 特性的替代方案：JSON 字段 + 索引)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    chain TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    full_data JSON NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            
            # 索引优化
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signals_token ON signals(token_address)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(timestamp DESC)")
            await db.commit()

    async def save_signal(self, signal: StandardizedSignal):
        """保存标准化信号"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO signals (id, chain, token_address, signal_type, full_data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    signal.id, 
                    signal.chain.value, 
                    signal.token.address, 
                    signal.signal_type.value, 
                    json.dumps(signal.to_dict()), 
                    signal.timestamp
                )
            )
            await db.commit()

    async def get_recent_signals(self, limit: int = 50) -> List[dict]:
        """获取最近的信号列表"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT full_data FROM signals ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [json.loads(row['full_data']) for row in rows]
