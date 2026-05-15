import httpx
import discord
from discord.ext import commands
import asyncio
from .interfaces import INotifier
from .models import StandardizedSignal
from .config import config


class WeComNotifier(INotifier):
    """企业微信 Webhook 推送"""
    def __init__(self):
        self.webhook_url = config.get("notifiers.wecom.webhook_url")

    async def notify(self, signal: StandardizedSignal):
        if not self.webhook_url:
            print("WeCom Webhook URL not configured, skipping...")
            return

        title = "🚀 **发现潜在优质土狗项目**" if signal.security.lp_burned else "⚠️ **新池检测 (未扣底)**"
        content = (
            f"{title}\n\n"
            f"> **Chain**: {signal.chain.value.upper()}\n"
            f"> **Token**: `{signal.token.symbol}`\n"
            f"> **Address**: `{signal.token.address}`\n"
            f"> **Signal**: {signal.signal_type.value}\n"
            f"> **Liquidity**: ${signal.data.get('liquidity', 0):,.2f}\n\n"
            f"**Security Check:**\n"
            f"- Mint Revoked: {'✅' if signal.security.mint_revoked else '❌'}\n"
            f"- Freeze Revoked: {'✅' if signal.security.freeze_revoked else '❌'}\n"
            f"- LP Burned: {'✅' if signal.security.lp_burned else '❌'}\n\n"
            f"[查看链接](https://dexscreener.com/solana/{signal.token.address})"
        )
        payload = {"msgtype": "markdown", "markdown": {"content": content}}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload, timeout=10)
                if response.status_code == 200:
                    print(f"[OK] WeCom 推送成功: {signal.token.symbol}")
                else:
                    print(f"[ERROR] WeCom 推送失败: {response.text}")
        except Exception as e:
            print(f"[ERROR] WeCom 推送异常: {e}")


class DiscordBotNotifier(INotifier, commands.Bot):
    """Discord 机器人：推送 + 命令交互"""
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        token = config.get("notifiers.discord.bot_token") or config.get("notifiers.discord_token")
        print(f"[DEBUG] Discord 模块初始化，Token 存在: {bool(token)}")

        commands.Bot.__init__(self, command_prefix="!", intents=intents)
        self.channel_id = config.get("notifiers.discord.channel_id") or config.get("notifiers.discord_channel_id")
        self.token = token
        self._proxy_url = config.get("app.proxy")
        self.start_time = asyncio.get_event_loop().time()

        @self.event
        async def on_ready():
            print(f"[INFO] ✅ Discord Bot 已连接: {self.user.name} ({self.user.id})")

        @self.command(name="status")
        async def _status(ctx):
            uptime = asyncio.get_event_loop().time() - self.start_time
            await ctx.send(f"🤖 **系统运行状态**:\n- 运行时间: {uptime:.0f}s\n- 当前监听链: Solana\n- 过滤器: `{config.get('filters')}`")

        @self.command(name="set_min_liq")
        async def _set_min_liq(ctx, value: int):
            config.set("filters.min_liquidity", value)
            await ctx.send(f"✅ 流动性过滤阈值已更新为: `${value}`")

        @self.command(name="toggle_mint")
        async def _toggle_mint(ctx, value: str):
            enabled = value.lower() == "on"
            config.set("filters.require_mint_disabled", enabled)
            await ctx.send(f"✅ Mint 权限强制检查已设置为: `{'开启' if enabled else '关闭'}`")

    async def notify(self, signal: StandardizedSignal):
        if not self.token or not self.channel_id:
            return

        channel = self.get_channel(int(self.channel_id))
        if not channel:
            print(f"[WARN] Discord 频道不可用: {self.channel_id}")
            return

        embed = discord.Embed(
            title="🚀 发现新信号" if signal.security.lp_burned else "⚠️ 新池检测",
            color=discord.Color.green() if signal.security.lp_burned else discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Token", value=f"`{signal.token.symbol}`", inline=True)
        embed.add_field(name="Chain", value=signal.chain.value.upper(), inline=True)
        embed.add_field(name="Address", value=f"`{signal.token.address}`", inline=False)
        embed.add_field(name="Security", value=(
            f"Mint Revoked: {'✅' if signal.security.mint_revoked else '❌'}\n"
            f"Freeze Revoked: {'✅' if signal.security.freeze_revoked else '❌'}\n"
            f"LP Burned: {'✅' if signal.security.lp_burned else '❌'}"
        ), inline=False)
        embed.set_footer(text=f"Signal: {signal.signal_type.value}")

        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[ERROR] Discord 推送失败: {e}")

    async def start_bot(self):
        if not self.token:
            print("[WARN] Discord Token 为空，跳过启动")
            return

        proxy = self._proxy_url
        try:
            if proxy:
                print(f"[INFO] 正在通过代理连接 Discord: {proxy}")
                from aiohttp_socks import ProxyConnector
                self.http.connector = ProxyConnector.from_url(proxy)
                print("[INFO] 代理 Connector 已注入")

            await self.start(self.token)
        except Exception as e:
            print(f"[ERROR] Discord Bot 登录失败: {e}")
            import traceback
            traceback.print_exc()
