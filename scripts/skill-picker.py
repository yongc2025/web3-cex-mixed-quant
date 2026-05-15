#!/usr/bin/env python3
"""
Vibe Coding 技能推荐脚本（v2）

根据项目类型，从 vibe-coding-cn 的 37 个 Skills 中推荐必装和可选 Skills，
输出安装清单（含 CLAUDE.md 引用格式和 vibe-init.sh 命令）。

使用方法：
    python assets/scripts/skill-picker.py --type quant-crypto
    python assets/scripts/skill-picker.py --type enterprise
    python assets/scripts/skill-picker.py --list
    python assets/scripts/skill-picker.py --search telegram
    python assets/scripts/skill-picker.py --interactive

依赖：Python 3.11+ 标准库。
"""

import argparse
import sys

# ============================================================
# 全部 37 个 Skills（基于 assets/skills/ 实际内容）
# ============================================================

ALL_SKILLS = {
    # ── 元技能 ──
    "skills-skills": {
        "name": "元技能：生成 Skills 的 Skills",
        "domain": "元技能",
        "desc": "从文档/代码/API 生成新的 SKILL.md",
    },
    "sop-generator": {
        "name": "SOP 生成器",
        "domain": "元技能",
        "desc": "将需求/流程规范化为可执行 SOP",
    },
    # ── AI 工具 ──
    "canvas-dev": {
        "name": "Canvas 白板驱动开发",
        "domain": "AI 工具",
        "desc": "AI 架构总师，Canvas 白板驱动的项目架构设计",
    },
    "ddd-doc-steward": {
        "name": "文档驱动开发管家",
        "domain": "AI 工具",
        "desc": "文档驱动开发（DDD），需求→技术→API 文档全链路",
    },
    "headless-cli": {
        "name": "无头 AI CLI",
        "domain": "AI 工具",
        "desc": "无头模式批量调用 Gemini/Claude/Codex CLI",
    },
    "tmux-autopilot": {
        "name": "tmux 自动化操控",
        "domain": "AI 工具",
        "desc": "tmux 自动化，AI 蜂群协作，多 Agent 并行开发",
    },
    "claude-code-guide": {
        "name": "Claude Code 使用指南",
        "domain": "AI 工具",
        "desc": "Claude Code CLI 使用最佳实践",
    },
    "claude-cookbooks": {
        "name": "Claude API 最佳实践",
        "domain": "AI 工具",
        "desc": "Claude API 使用示例和最佳实践",
    },
    # ── 数据库 ──
    "postgresql": {
        "name": "PostgreSQL 专家",
        "domain": "数据库",
        "desc": "数据库设计、查询优化、索引策略、性能调优",
    },
    "timescaledb": {
        "name": "TimescaleDB 时序扩展",
        "domain": "数据库",
        "desc": "PostgreSQL 时序数据库扩展，适合时间序列数据",
    },
    # ── 量化交易 ──
    "ccxt": {
        "name": "ccxt 交易所统一 API",
        "domain": "量化交易",
        "desc": "支持 150+ 加密货币交易所的统一 API 封装",
    },
    "coingecko": {
        "name": "CoinGecko 行情 API",
        "domain": "量化交易",
        "desc": "CoinGecko 行情/基本面数据 API",
    },
    "cryptofeed": {
        "name": "cryptofeed 实时数据流",
        "domain": "量化交易",
        "desc": "加密货币实时 WebSocket tick 级行情推送",
    },
    "hummingbot": {
        "name": "Hummingbot 量化交易框架",
        "domain": "量化交易",
        "desc": "量化交易机器人框架，做市/套利策略",
    },
    "polymarket": {
        "name": "Polymarket 预测市场",
        "domain": "量化交易",
        "desc": "预测市场 API 集成",
    },
    "backtesting": {
        "name": "回测引擎",
        "domain": "量化交易",
        "desc": "backtrader/vnpy 回测框架",
    },
    "risk-management": {
        "name": "风控模块",
        "domain": "量化交易",
        "desc": "仓位/止损/熔断风控",
    },
    "quant-factor": {
        "name": "因子分析",
        "domain": "量化交易",
        "desc": "因子挖掘/IC 分析/多因子组合",
    },
    "tushare-akshare": {
        "name": "A 股数据源",
        "domain": "量化交易",
        "desc": "tushare/akshare A 股数据接口",
    },
    "alpaca-polygon": {
        "name": "美股数据源",
        "domain": "量化交易",
        "desc": "Alpaca/Polygon.io 美股数据接口",
    },
    # ── 开发工具 ──
    "telegram-dev": {
        "name": "Telegram Bot 开发",
        "domain": "开发工具",
        "desc": "Telegram Bot 开发完整指南（API、消息处理、键盘、Webhook）",
    },
    "twscrape": {
        "name": "Twitter/X 数据抓取",
        "domain": "开发工具",
        "desc": "Twitter/X 社交媒体数据抓取工具",
    },
    "snapdom": {
        "name": "snapdom DOM 快照",
        "domain": "开发工具",
        "desc": "DOM 快照与 UI 测试",
    },
    "proxychains": {
        "name": "proxychains 代理链",
        "domain": "开发工具",
        "desc": "代理链配置与使用，解决网络访问限制",
    },
    "wechat-mp": {
        "name": "微信小程序原生开发",
        "domain": "开发工具",
        "desc": "微信小程序框架、云开发、微信支付、订阅消息",
    },
    "flutter": {
        "name": "Flutter 跨平台开发",
        "domain": "开发工具",
        "desc": "Flutter SDK、Dart、Widget 体系、Riverpod/Bloc 状态管理、多端发布",
    },
    "react-native": {
        "name": "React Native 开发",
        "domain": "开发工具",
        "desc": "React Native 核心组件、Expo 工作流、原生模块桥接、OTA 热更新",
    },
    "uniapp": {
        "name": "UniApp 跨平台开发",
        "domain": "开发工具",
        "desc": "UniApp + Vue3 + TypeScript，多端发布（微信/支付宝/百度/字节小程序 + H5 + APP）",
    },
    # ── 生产力 ──
    "markdown-to-epub": {
        "name": "Markdown 转 EPUB",
        "domain": "生产力",
        "desc": "Markdown 转 EPUB 电子书",
    },
    # ── 企业级 ──
    "event-driven": {
        "name": "事件驱动架构",
        "domain": "企业级",
        "desc": "事件驱动架构设计",
    },
    "microservice": {
        "name": "微服务架构",
        "domain": "企业级",
        "desc": "微服务架构设计",
    },
    "rbac": {
        "name": "RBAC 权限管理",
        "domain": "企业级",
        "desc": "RBAC 权限管理",
    },
    "workflow-engine": {
        "name": "工作流引擎",
        "domain": "企业级",
        "desc": "工作流引擎设计",
    },
    "message-queue": {
        "name": "消息队列",
        "domain": "企业级",
        "desc": "RabbitMQ/Kafka/RocketMQ/Redis Stream 消息队列设计与实现",
    },
    # ── SaaS ──
    "multi-tenant": {
        "name": "多租户架构",
        "domain": "SaaS",
        "desc": "多租户架构设计",
    },
    "oauth-sso": {
        "name": "OAuth2/SSO 认证",
        "domain": "SaaS",
        "desc": "OAuth2/SSO 认证集成",
    },
    "billing-sub": {
        "name": "计费/订阅系统",
        "domain": "SaaS",
        "desc": "Stripe API 集成、订阅管理、发票生成、用量计费、套餐管理",
    },
}

# 基础技能（所有项目共用）
BASE_SKILLS = ["skills-skills", "sop-generator", "canvas-dev", "headless-cli"]

# 项目类型映射（与 vibe-init.sh 保持一致）
PROJECT_TYPES = {
    "quant-crypto": {
        "name": "加密货币量化",
        "required": ["ccxt", "cryptofeed", "hummingbot", "coingecko", "polymarket", "postgresql", "timescaledb", "proxychains"],
        "optional": ["backtesting", "risk-management"],
    },
    "quant-astock": {
        "name": "A 股量化",
        "required": ["postgresql", "timescaledb"],
        "optional": ["tushare-akshare", "quant-factor", "backtesting"],
    },
    "quant-usstock": {
        "name": "美股量化",
        "required": ["postgresql", "timescaledb", "twscrape", "proxychains"],
        "optional": ["alpaca-polygon", "quant-factor"],
    },
    "app": {
        "name": "APP/小程序",
        "required": ["canvas-dev", "ddd-doc-steward", "snapdom"],
        "optional": ["flutter", "react-native", "uniapp", "wechat-mp"],
    },
    "enterprise": {
        "name": "企业级应用",
        "required": ["canvas-dev", "ddd-doc-steward", "sop-generator", "postgresql", "claude-cookbooks"],
        "optional": ["rbac", "workflow-engine", "microservice", "event-driven", "message-queue"],
    },
    "saas": {
        "name": "互联网 SaaS",
        "required": ["canvas-dev", "ddd-doc-steward", "sop-generator", "postgresql", "telegram-dev", "snapdom"],
        "optional": ["multi-tenant", "oauth-sso", "billing-sub", "event-driven", "message-queue"],
    },
}


def print_all_skills():
    print(f"\n📚 vibe-coding-cn Skills 列表（共 {len(ALL_SKILLS)} 个）\n")
    by_domain = {}
    for key, info in ALL_SKILLS.items():
        by_domain.setdefault(info["domain"], []).append((key, info))
    for domain, skills in by_domain.items():
        print(f"  [{domain}]")
        for key, info in skills:
            print(f"    • {key:<22} {info['desc']}")
        print()


def print_recommendation(project_type: str):
    if project_type not in PROJECT_TYPES:
        print(f"\n❌ 未知类型: {project_type}")
        print(f"可用类型: {', '.join(PROJECT_TYPES.keys())}")
        sys.exit(1)

    info = PROJECT_TYPES[project_type]
    print(f"\n{'═' * 55}")
    print(f"  🎯 {info['name']}")
    print(f"{'═' * 55}")

    print(f"\n🏠 基础技能（所有项目共用）:\n")
    for s in BASE_SKILLS:
        sk = ALL_SKILLS[s]
        print(f"  • {s:<22} {sk['desc']}")

    print(f"\n🔴 必装 Skills ({len(info['required'])} 个):\n")
    for s in info["required"]:
        sk = ALL_SKILLS[s]
        print(f"  • {s:<22} {sk['desc']}")

    if info["optional"]:
        print(f"\n🟡 可选 Skills ({len(info['optional'])} 个):\n")
        for s in info["optional"]:
            sk = ALL_SKILLS[s]
            print(f"  • {s:<22} {sk['desc']}")

    # vibe-init.sh 命令
    print(f"\n{'─' * 55}")
    print(f"\n🚀 一键创建项目:\n")
    print(f"  ./vibe-init.sh --type {project_type} --name my-project")

    # CLAUDE.md 引用（去重）
    all_skills = list(dict.fromkeys(BASE_SKILLS + info["required"]))
    print(f"\n📋 CLAUDE.md 引用:\n")
    print("  ```markdown")
    print("  ## 参考技能")
    for s in all_skills:
        print(f"  @skills/{s}/SKILL.md")
    for s in info["optional"]:
        print(f"  # @skills/{s}/SKILL.md  # 可选")
    print("  ```")


def print_search(query: str):
    print(f"\n🔍 搜索: {query}\n")
    query_lower = query.lower()
    results = [
        (k, v) for k, v in ALL_SKILLS.items()
        if query_lower in f"{k} {v['name']} {v['desc']} {v['domain']}".lower()
    ]
    if results:
        for key, info in results:
            print(f"  • {key:<22} [{info['domain']}] {info['desc']}")
    else:
        print("  未找到匹配项。")
        print("\n  💡 用元技能生成新 Skill: cat assets/skills/skills-skills/SKILL.md")


def print_interactive():
    print(f"\n🚀 Vibe Coding 技能推荐（共 {len(ALL_SKILLS)} 个 Skills）\n")
    types = list(PROJECT_TYPES.items())
    for i, (key, info) in enumerate(types, 1):
        print(f"  [{i}] {info['name']} ({key})")
    print()
    try:
        choice = input("选择编号: ").strip()
        idx = int(choice) - 1
        if 0 <= idx < len(types):
            print_recommendation(types[idx][0])
        else:
            print("❌ 无效编号")
    except (ValueError, KeyboardInterrupt):
        print("\n已取消。")


def main():
    parser = argparse.ArgumentParser(
        description="Vibe Coding 技能推荐工具（37 个 Skills）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  %(prog)s --type quant-crypto\n"
               "  %(prog)s --type enterprise\n"
               "  %(prog)s --list\n"
               "  %(prog)s --search telegram\n"
               "  %(prog)s --interactive\n",
    )
    parser.add_argument("--type", "-t", choices=list(PROJECT_TYPES.keys()), help="项目类型")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有 Skills")
    parser.add_argument("--search", "-s", metavar="KEYWORD", help="搜索 Skills")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式选择")
    args = parser.parse_args()

    if args.list:
        print_all_skills()
    elif args.search:
        print_search(args.search)
    elif args.type:
        print_recommendation(args.type)
    elif args.interactive:
        print_interactive()
    else:
        print_interactive()


if __name__ == "__main__":
    main()
