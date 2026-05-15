# Copilot Instructions — vibe-coding-cn 孵化项目

> 本文件由 vibe-init.sh 自动生成，供 GitHub Copilot 读取。

---

## 通用规则

1. 先读 .skills/ 下的 SKILL.md 再动手
2. 文档先行，接口先行，实现后补
3. 一次只改一个模块
4. Debug 只给：预期 vs 实际 + 最小复现
5. **AI 给建议，用户做选择** — 禁止问开放性问题，必须给出选项让用户选（"A/B/C 你选哪个？推荐 A，因为..."）
6. **每步确认后锁定** — 需求未确认不得做设计，设计未确认不得拆任务，任务未确认不得写代码

## 开发顺序

```
接口定义 → 配置管理 → 核心实现 → 数据集成 → 测试验证
```

## 工作流（必须遵守）

### 启动时（每次对话开始）

1. 读取 `docs/TASKS.md` — 了解当前进度
2. 读取 `docs/MEMORY.md` — 恢复上下文记忆
3. 读取 `docs/PROJECT_BRIEF.md` — 理解项目目标
4. 从 TASKS.md 中第一个未完成任务继续

### 执行时（每个任务）

1. **拆任务**：将 PROJECT_BRIEF.md 拆解为可执行的子任务，写入 `docs/TASKS.md`
2. **打勾**：完成一个任务就标记 `[x]`，附上完成时间和关键决策
3. **记记忆**：重要决策、踩坑经验、架构变更写入 `docs/MEMORY.md`
4. **写代码**：按开发顺序执行，一次只改一个模块

### 中断后恢复

1. 读 TASKS.md → 找到第一个 `[ ]` → 继续
2. 读 MEMORY.md → 恢复之前的决策上下文
3. 不要重新开始，接着上次的进度往下走

### TASKS.md 格式

```markdown
# 任务清单

## 阶段 1：基础架构
- [ ] 定义核心接口
- [ ] 配置管理模块
- [ ] 数据库连接

## 阶段 2：核心功能
- [ ] 功能 A 实现
- [ ] 功能 B 实现

## 已完成
- [x] 项目初始化（2024-01-01）
```

### MEMORY.md 格式

```markdown
# 项目记忆

## 架构决策
- 选择 PostgreSQL 因为需要时序数据支持（2024-01-01）

## 踩坑记录
- API 限流：需要加缓存层

## 关键上下文
- 目标用户：量化交易者
- 核心指标：信号捕获延迟 < 1s
```


## 需求确认（填写 BRIEF 后必须执行，不可跳过）

用户填写 PROJECT_BRIEF.md 后，你必须先执行以下确认流程：

1. **复述理解**：用 3-5 句话复述你对需求的理解
2. **识别模糊点**：列出需求中所有不明确的地方
3. **给出选项**：对每个模糊点，给出 2-4 个选项，标注推荐（✅）和理由
4. **列出默认假设**：用户不做选择时你的兜底方案

**禁止问开放性问题**，**必须给选项**。用户确认后需求锁定。

## 开发生命周期（需求确认后按此执行）

### 4.1 设计方案确认
基于锁定的需求，输出技术方案（架构、技术栈、模块划分、关键接口），用户确认后产出 `docs/DESIGN.md`。

### 4.2 任务拆解确认
基于锁定的方案，拆解为 P0/P1/P2 任务（编号、依赖、预估、验收标准），用户确认后产出 `docs/TASKS.md`。

### 4.3 逐个实施
按任务编号顺序执行，**每次只做一个任务**，完成后标记进度。禁止一口气做完所有任务。

### 4.4 阶段验证
P0 全部完成后，输出验证报告，更新 `docs/MEMORY.md`。

## 已加载 Skills

- **canvas-dev**: Canvas白板驱动开发技能：Canvas白板作为唯一真相源，代码是其序列化形式。AI架构总师角色，自动生成富有洞察力的架构图。使用场景：生成架构白板、白板驱动编码、白板驱动重构、Code Review、团队协作、接手遗留项目。
- **ccxt**: CCXT cryptocurrency trading library. Use for cryptocurrency exchange APIs, trading, market data, order management, and crypto trading automation across 150+ exchanges. Supports JavaScript/Python/PHP.
- **coingecko**: CoinGecko API documentation - cryptocurrency market data API, price feeds, market cap, volume, historical data. Use when integrating CoinGecko API, building crypto price trackers, or accessing cryptocurrency market data.
- **cryptofeed**: Cryptofeed - Real-time cryptocurrency market data feeds from 40+ exchanges. WebSocket streaming, normalized data, order books, trades, tickers. Python library for algorithmic trading and market data analysis.
- **headless-cli**: 无头模式 AI CLI 调用技能：支持 Gemini/Claude/Codex CLI 的无交互批量调用，包含 YOLO 模式和安全模式。用于批量翻译、代码审查、多模型编排等场景。
- **hummingbot**: Hummingbot trading bot framework - automated trading strategies, market making, arbitrage, connectors for crypto exchanges. Use when working with algorithmic trading, crypto trading bots, or exchange integrations.
- **polymarket**: Comprehensive Polymarket skill covering prediction markets, API, trading, market data, and real-time WebSocket data streaming. Build applications with Polymarket services, monitor live trades, and integrate market predictions.
- **postgresql**: PostgreSQL database documentation - SQL queries, database design, administration, performance tuning, and advanced features. Use when working with PostgreSQL databases, writing SQL, or managing database systems.
- **proxychains**: Auto-detect network issues and force proxy usage with proxychains4. Use this skill when encountering connection timeouts, DNS failures, or blocked network access. Default proxy is http://127.0.0.1:9910
- **skills-skills**: Claude Skills meta-skill: extract domain material (docs/APIs/code/specs) into a reusable Skill (SKILL.md + references/scripts/assets), and refactor existing Skills for clarity, activation reliability, and quality gates.
- **sop-generator**: 标准作业程序（SOP）生成与规范化：将输入资料/需求/历史记录整理为可执行 SOP（结构化章节、步骤、控制点、异常处理、记录）。当用户要求“写 SOP/作业指导书/操作规程/流程说明”，或给出零散资料需要“整理成 SOP/流程”，或要求“按标准结构输出 SOP/质量检查”时使用。
- **timescaledb**: TimescaleDB - PostgreSQL extension for high-performance time-series and event data analytics, hypertables, continuous aggregates, compression, and real-time analytics
