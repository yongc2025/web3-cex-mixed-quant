#!/bin/bash
# ============================================================
# vibe-init.sh — 从母机初始化新项目（完整孵化版）
# 用法: ./vibe-init.sh --ai <助手> --type <类型> [--name <项目名>] [--skills <额外技能>]
# ============================================================

set -e

# ── 颜色（终端不支持时自动禁用）──────────────────────────────
if [ -t 1 ] && [ -n "$TERM" ] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; CYAN=''; NC=''
fi

# ── 母机远程地址 ──────────────────────────────────────────────
VIBE_REMOTE_URL="https://github.com/yongc2025/vibe-coding-cn.git"

# ── 网络诊断结果（全局） ──────────────────────────────────────
VIBE_CLONE_DIAGNOSIS=""

# ── 帮助 ──────────────────────────────────────────────────────
usage() {
    cat <<EOF
${BLUE}vibe-init.sh${NC} — 从母机初始化新项目（完整孵化版）

${YELLOW}用法:${NC}
  bash vibe-init.sh --ai <助手> --type <类型> [选项]
  bash vibe-init.sh --ai copilot --type quant-crypto --name .  # 在当前目录初始化

${YELLOW}AI 助手 (--ai):${NC}
  claude        生成 CLAUDE.md（Claude Code）
  cursor        生成 .cursorrules（Cursor）
  copilot       生成 .github/copilot-instructions.md（GitHub Copilot）
  windsurf      生成 .windsurfrules（Windsurf）
  cline         生成 .clinerules（Cline）
  codex         生成 AGENTS.md（OpenAI Codex）
  all           生成以上所有文件（默认）

${YELLOW}项目类型 (--type):${NC}
  quant-crypto    加密货币量化（ccxt + cryptofeed + hummingbot + timescaledb）
  quant-astock    A股量化（tushare + akshare + timescaledb）
  quant-usstock   美股量化（alpaca + polygon + timescaledb）
  app             APP/小程序（canvas-dev + ddd-doc-steward）
  enterprise      企业级应用（canvas-dev + ddd-doc-steward + sop-generator）
  saas            互联网SaaS（canvas-dev + ddd-doc-steward + sop-generator）
  custom          自定义（需手动指定 --skills）

${YELLOW}选项:${NC}
  --type <类型>       项目类型（必填）
  --ai <助手>         AI 助手类型（默认: all）
  --name <名称>       项目目录名（默认: my-<类型>-project），传 . 表示当前目录
  --dir <路径>        项目创建目录（默认: 当前目录）
  --skills <技能列表>  额外技能，逗号分隔
  --no-workflow       不复制 auto-dev-loop 工作流（默认复制）
  --no-codex          不复制 .codex/ 配置
  --no-agents         不复制 AGENTS.md
  --no-docs           不复制方法论文档和案例研究
  --dry-run           只显示会做什么，不实际执行
  --help              显示此帮助

${YELLOW}示例:${NC}
  bash vibe-init.sh --ai claude --type quant-crypto --name my-bot
  bash vibe-init.sh --ai cursor --type app --name my-app --skills twscrape,telegram-dev
  bash vibe-init.sh --ai all --type custom --skills ccxt,postgresql,canvas-dev
  bash vibe-init.sh --type quant-crypto --name my-bot --dry-run
EOF
    exit 0
}

# ── 网络连通性检测 ────────────────────────────────────────────
check_github_connectivity() {
    local err_output="$1"
    if ! host github.com >/dev/null 2>&1 && ! nslookup github.com >/dev/null 2>&1; then
        VIBE_CLONE_DIAGNOSIS="network"
        return
    fi
    if ! curl -sI --connect-timeout 5 --max-time 10 https://github.com >/dev/null 2>&1; then
        VIBE_CLONE_DIAGNOSIS="network"
        return
    fi
    if echo "$err_output" | grep -qiE "timeout|timed out|couldn't connect|couldn't resolve|network|connection refused|Connection reset|proxy|SSL|certificate"; then
        VIBE_CLONE_DIAGNOSIS="network"
        return
    fi
    if echo "$err_output" | grep -qiE "authentication|permission|403|401|fatal: unable to access"; then
        VIBE_CLONE_DIAGNOSIS="auth"
        return
    fi
    VIBE_CLONE_DIAGNOSIS="unknown"
}

# ── 打印网络问题指引 ──────────────────────────────────────────
print_network_help() {
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ❌ 网络无法访问 GitHub${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  脚本需要从 GitHub 下载母机资源，但当前网络不通。"
    echo ""
    echo -e "${YELLOW}  解决方案（任选其一）：${NC}"
    echo ""
    echo -e "  ${GREEN}方案 1：设置代理后重试${NC}"
    echo -e "    export https_proxy=http://127.0.0.1:7890"
    echo -e "    export http_proxy=http://127.0.0.1:7890"
    echo -e "    bash vibe-init.sh --ai copilot --type quant-crypto --name my-bot"
    echo ""
    echo -e "  ${GREEN}方案 2：手动克隆母机到本地${NC}"
    echo -e "    git clone --depth 1 $VIBE_REMOTE_URL ~/vibe-coding-cn"
    echo -e "    bash vibe-init.sh --ai copilot --type quant-crypto --name my-bot"
    echo ""
    echo -e "  ${GREEN}方案 3：用 GitHub 镜像${NC}"
    echo -e "    git clone --depth 1 https://ghproxy.com/$VIBE_REMOTE_URL ~/vibe-coding-cn"
    echo -e "    bash vibe-init.sh --ai copilot --type quant-crypto --name my-bot"
    echo ""
    echo -e "  ${GREEN}方案 4：设置环境变量指向已有母机${NC}"
    echo -e "    export VIBE_MACHINE_DIR=/path/to/vibe-coding-cn"
    echo -e "    bash vibe-init.sh --ai copilot --type quant-crypto --name my-bot"
    echo ""
}

# ── 母机目录检测 ──────────────────────────────────────────────
detect_machine_dir() {
    if [ -n "$VIBE_MACHINE_DIR" ] && [ -d "$VIBE_MACHINE_DIR/assets/skills" ]; then
        echo "$VIBE_MACHINE_DIR"
        return
    fi
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -d "$script_dir/assets/skills" ]; then
        echo "$script_dir"
        return
    fi
    local default_dir="$HOME/vibe-coding-cn"
    if [ -d "$default_dir/assets/skills" ]; then
        echo "$default_dir"
        return
    fi
    local ws_dir="$HOME/.openclaw/workspace/vibe-coding-cn"
    if [ -d "$ws_dir/assets/skills" ]; then
        echo "$ws_dir"
        return
    fi

    echo -e "${YELLOW}本地未找到母机，正在从 GitHub 下载...${NC}" >&2
    local temp_dir
    temp_dir=$(mktemp -d)
    local clone_err
    clone_err=$(mktemp)

    if git clone --depth 1 --filter=blob:none --sparse \
        "$VIBE_REMOTE_URL" "$temp_dir/vibe-coding-cn" 2>"$clone_err"; then
        (cd "$temp_dir/vibe-coding-cn" && \
         git sparse-checkout set assets/skills assets/config assets/workflow assets/documents assets/prompts assets/scripts docs/onboarding 2>/dev/null) || true
        if [ -d "$temp_dir/vibe-coding-cn/assets/skills" ]; then
            echo -e "${GREEN}✓ 母机已下载到: $temp_dir/vibe-coding-cn${NC}" >&2
            rm -f "$clone_err"
            echo "$temp_dir/vibe-coding-cn"
            return
        fi
    fi

    check_github_connectivity "$(cat "$clone_err" 2>/dev/null)"
    rm -f "$clone_err"
    echo ""
}

# ── 技能映射 ──────────────────────────────────────────────────
declare -A TYPE_SKILLS
TYPE_SKILLS[quant-crypto]="ccxt,cryptofeed,hummingbot,coingecko,polymarket,postgresql,timescaledb,proxychains"
TYPE_SKILLS[quant-astock]="postgresql,timescaledb"
TYPE_SKILLS[quant-usstock]="postgresql,timescaledb,twscrape,proxychains"
TYPE_SKILLS[app]="canvas-dev,ddd-doc-steward,snapdom"
TYPE_SKILLS[enterprise]="canvas-dev,ddd-doc-steward,sop-generator,postgresql,claude-cookbooks"
TYPE_SKILLS[saas]="canvas-dev,ddd-doc-steward,sop-generator,postgresql,telegram-dev,snapdom"

BASE_SKILLS="skills-skills,sop-generator,canvas-dev,headless-cli"

# ── AI 助手入口文件生成 ───────────────────────────────────────

generate_claude_md() {
    local full_path="$1"
    local skill_list="$2"
    local machine_dir="$3"
    cat > "$full_path/CLAUDE.md" << 'EOF'
# CLAUDE.md — vibe-coding-cn 孵化项目

> 本文件由 vibe-init.sh 自动生成，供 Claude Code 读取。

---

## 通用规则

1. **先读 .skills/ 下的 SKILL.md 再动手** — 每个文件包含该领域的完整知识
2. **文档先行，接口先行，实现后补** — 先定义输入输出再写实现
3. **一次只改一个模块** — 保持专注，不要顺手重构
4. **Debug 只给**：预期 vs 实际 + 最小复现
5. **AI 给建议，用户做选择** — 禁止问开放性问题（"你想怎么做？"），必须给出选项让用户选（"A/B/C 你选哪个？推荐 A，因为..."）
6. **每步确认后锁定** — 需求未确认不得做设计，设计未确认不得拆任务，任务未确认不得写代码

## 开发顺序

```
接口定义 → 配置管理 → 核心实现 → 数据集成 → 测试验证
```

## 参考技能

EOF
    IFS=',' read -ra skills_arr <<< "$skill_list"
    for skill in "${skills_arr[@]}"; do
        skill=$(echo "$skill" | xargs)
        if [ -d "$full_path/.skills/$skill" ]; then
            echo "@.skills/$skill/SKILL.md" >> "$full_path/CLAUDE.md"
        fi
    done

    cat >> "$full_path/CLAUDE.md" << 'EOF'

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


## 项目定义

创建项目后，请填写 `docs/PROJECT_BRIEF.md`：

1. **目标**：我要解决什么问题？
2. **现状**：当前是什么情况？
3. **差距**：从现状到目标，缺什么？
4. **判断标准**：怎么知道做完了？

## 需求确认（填写 BRIEF 后必须执行，不可跳过）

用户填写 PROJECT_BRIEF.md 后，你必须先执行以下确认流程：

1. **复述理解**：用 3-5 句话复述你对需求的理解
2. **识别模糊点**：列出需求中所有不明确的地方
3. **给出选项**：对每个模糊点，给出 2-4 个选项，标注推荐（✅）和理由
4. **列出默认假设**：用户不做选择时你的兜底方案

**禁止问开放性问题**（"你想怎么做？"），**必须给选项**（"A/B/C 你选哪个？推荐 A，因为..."）

用户确认后（回复选择或"都按推荐"），需求锁定。后续开发基于锁定的需求进行。

## 开发生命周期（需求确认后按此执行）

### 4.1 设计方案确认
基于锁定的需求，输出技术方案（架构、技术栈、模块划分、关键接口），用户确认后产出 `docs/DESIGN.md`。

### 4.2 任务拆解确认
基于锁定的方案，拆解为 P0/P1/P2 任务（编号、依赖、预估、验收标准），用户确认后产出 `docs/TASKS.md`。

### 4.3 逐个实施
按任务编号顺序执行，**每次只做一个任务**，完成后标记进度。禁止一口气做完所有任务。遇到阻塞给出方案让用户选。

### 4.4 阶段验证
P0 全部完成后，输出验证报告，更新 `docs/MEMORY.md`。

## 参考资料

- 方法论文档：`docs/reference/principles/`
- 案例研究：`docs/reference/case-studies/`
- 提示词库：`docs/reference/prompts/`
- 开发指南：`docs/reference/guides/`
EOF
    echo -e "  ${GREEN}✓${NC} CLAUDE.md"
}

generate_cursorrules() {
    local full_path="$1"
    local skill_list="$2"
    cat > "$full_path/.cursorrules" << 'EOF'
# Cursor Rules — vibe-coding-cn 孵化项目

> 本文件由 vibe-init.sh 自动生成，供 Cursor 读取。

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

EOF
    IFS=',' read -ra skills_arr <<< "$skill_list"
    for skill in "${skills_arr[@]}"; do
        skill=$(echo "$skill" | xargs)
        if [ -d "$full_path/.skills/$skill" ]; then
            local desc
            desc=$(sed -n '/^---$/,/^---$/p' "$full_path/.skills/$skill/SKILL.md" 2>/dev/null | grep "description:" | head -1 | sed 's/^description: *//' | sed 's/^"//' | sed 's/"$//')
            echo "- **$skill**: $desc" >> "$full_path/.cursorrules"
        fi
    done
    echo -e "  ${GREEN}✓${NC} .cursorrules"
}

generate_copilot_instructions() {
    local full_path="$1"
    local skill_list="$2"
    mkdir -p "$full_path/.github"
    cat > "$full_path/.github/copilot-instructions.md" << 'EOF'
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

EOF
    IFS=',' read -ra skills_arr <<< "$skill_list"
    for skill in "${skills_arr[@]}"; do
        skill=$(echo "$skill" | xargs)
        if [ -d "$full_path/.skills/$skill" ]; then
            local desc
            desc=$(sed -n '/^---$/,/^---$/p' "$full_path/.skills/$skill/SKILL.md" 2>/dev/null | grep "description:" | head -1 | sed 's/^description: *//' | sed 's/^"//' | sed 's/"$//')
            echo "- **$skill**: $desc" >> "$full_path/.github/copilot-instructions.md"
        fi
    done
    echo -e "  ${GREEN}✓${NC} .github/copilot-instructions.md"
}

generate_windsurfrules() {
    local full_path="$1"
    local skill_list="$2"
    cat > "$full_path/.windsurfrules" << 'EOF'
# Windsurf Rules — vibe-coding-cn 孵化项目

> 本文件由 vibe-init.sh 自动生成，供 Windsurf 读取。

---

## 通用规则

1. 先读 .skills/ 下的 SKILL.md 再动手
2. 文档先行，接口先行，实现后补
3. 一次只改一个模块

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
4. **写代码**：一次只改一个模块

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

## 阶段 2：核心功能
- [ ] 功能 A 实现

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
```


## 已加载 Skills

EOF
    IFS=',' read -ra skills_arr <<< "$skill_list"
    for skill in "${skills_arr[@]}"; do
        skill=$(echo "$skill" | xargs)
        if [ -d "$full_path/.skills/$skill" ]; then
            local desc
            desc=$(sed -n '/^---$/,/^---$/p' "$full_path/.skills/$skill/SKILL.md" 2>/dev/null | grep "description:" | head -1 | sed 's/^description: *//' | sed 's/^"//' | sed 's/"$//')
            echo "- **$skill**: $desc" >> "$full_path/.windsurfrules"
        fi
    done
    echo -e "  ${GREEN}✓${NC} .windsurfrules"
}

generate_clinerules() {
    local full_path="$1"
    local skill_list="$2"
    cat > "$full_path/.clinerules" << 'EOF'
# Cline Rules — vibe-coding-cn 孵化项目

> 本文件由 vibe-init.sh 自动生成，供 Cline 读取。

---

## 通用规则

1. 先读 .skills/ 下的 SKILL.md 再动手
2. 文档先行，接口先行，实现后补
3. 一次只改一个模块

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
4. **写代码**：一次只改一个模块

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

## 阶段 2：核心功能
- [ ] 功能 A 实现

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
```


## 已加载 Skills

EOF
    IFS=',' read -ra skills_arr <<< "$skill_list"
    for skill in "${skills_arr[@]}"; do
        skill=$(echo "$skill" | xargs)
        if [ -d "$full_path/.skills/$skill" ]; then
            local desc
            desc=$(sed -n '/^---$/,/^---$/p' "$full_path/.skills/$skill/SKILL.md" 2>/dev/null | grep "description:" | head -1 | sed 's/^description: *//' | sed 's/^"//' | sed 's/"$//')
            echo "- **$skill**: $desc" >> "$full_path/.clinerules"
        fi
    done
    echo -e "  ${GREEN}✓${NC} .clinerules"
}

generate_agents_md() {
    local full_path="$1"
    local skill_list="$2"
    local machine_dir="$3"
    if [ -f "$machine_dir/AGENTS.md" ]; then
        cp "$machine_dir/AGENTS.md" "$full_path/AGENTS.md"
        echo -e "  ${GREEN}✓${NC} AGENTS.md"
    fi
}

# ── 解析参数 ──────────────────────────────────────────────────
TYPE=""
AI_TYPE="all"
PROJECT_NAME=""
PROJECT_DIR="."
EXTRA_SKILLS=""
WITH_WORKFLOW=true
NO_CODEX=false
NO_AGENTS=false
NO_DOCS=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --type)       TYPE="$2"; shift 2 ;;
        --ai)         AI_TYPE="$2"; shift 2 ;;
        --name)       PROJECT_NAME="$2"; shift 2 ;;
        --dir)        PROJECT_DIR="$2"; shift 2 ;;
        --skills)     EXTRA_SKILLS="$2"; shift 2 ;;
        --no-workflow) WITH_WORKFLOW=false; shift ;;
        --no-codex)   NO_CODEX=true; shift ;;
        --no-agents)  NO_AGENTS=true; shift ;;
        --no-docs)    NO_DOCS=true; shift ;;
        --dry-run)    DRY_RUN=true; shift ;;
        --help|-h)    usage ;;
        *)            echo -e "${RED}未知参数: $1${NC}"; usage ;;
    esac
done

if [ -z "$TYPE" ]; then
    echo -e "${RED}错误: 必须指定 --type${NC}"
    usage
fi

case "$AI_TYPE" in
    claude|cursor|copilot|windsurf|cline|codex|all) ;;
    *)  echo -e "${RED}错误: 未知的 AI 助手类型: $AI_TYPE${NC}"
        echo "支持: claude, cursor, copilot, windsurf, cline, codex, all"
        exit 1 ;;
esac

# ── 检测母机 ──────────────────────────────────────────────────
MACHINE_DIR=$(detect_machine_dir)
if [ -z "$MACHINE_DIR" ]; then
    case "$VIBE_CLONE_DIAGNOSIS" in
        network) print_network_help ;;
        *)
            echo -e "${RED}错误: 无法获取母机${NC}"
            echo ""
            echo "请通过以下方式之一提供母机："
            echo "  1. 设置环境变量: export VIBE_MACHINE_DIR=/path/to/vibe-coding-cn"
            echo "  2. 在母机目录内运行此脚本"
            echo "  3. 将母机克隆到 ~/vibe-coding-cn"
            echo "  4. 确保网络可访问 GitHub"
            ;;
    esac
    exit 1
fi

# ── 计算技能列表 ──────────────────────────────────────────────
SKILLS_LIST="$BASE_SKILLS"
if [ -n "${TYPE_SKILLS[$TYPE]}" ]; then
    SKILLS_LIST="$SKILLS_LIST,${TYPE_SKILLS[$TYPE]}"
fi
if [ -n "$EXTRA_SKILLS" ]; then
    SKILLS_LIST="$SKILLS_LIST,$EXTRA_SKILLS"
fi
SKILLS_LIST=$(echo "$SKILLS_LIST" | tr ',' '\n' | sort -u | tr '\n' ',' | sed 's/,$//')

# ── 项目目录 ──────────────────────────────────────────────────
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="my-${TYPE}-project"
fi
if [ "$PROJECT_NAME" = "." ]; then
    FULL_PATH="$PROJECT_DIR"
else
    FULL_PATH="$PROJECT_DIR/$PROJECT_NAME"
fi

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   vibe-init — 从母机孵化项目（完整版）           ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}类型:${NC}     $TYPE"
echo -e "  ${YELLOW}AI 助手:${NC}  $AI_TYPE"
echo -e "  ${YELLOW}项目:${NC}     $FULL_PATH"
echo -e "  ${YELLOW}技能:${NC}     $SKILLS_LIST"
echo -e "  ${YELLOW}母机:${NC}     $MACHINE_DIR"
echo ""

if $DRY_RUN; then
    echo -e "${YELLOW}[DRY RUN] 以下操作不会实际执行${NC}"
    echo ""
fi

run() {
    if $DRY_RUN; then
        echo -e "  ${BLUE}[DRY]${NC} $*"
    else
        "$@"
    fi
}

# =============================================================
#  完整孵化流程 — 9 步
# =============================================================

# ── [1/9] 创建项目骨架 ───────────────────────────────────────
echo -e "${GREEN}[1/9] 创建项目骨架...${NC}"
run mkdir -p "$FULL_PATH"/{docs,src,tests}

# ── [2/9] 复制 .codex/ 配置 ──────────────────────────────────
if ! $NO_CODEX; then
    echo -e "${GREEN}[2/9] 复制 .codex/ 配置...${NC}"
    if [ -d "$MACHINE_DIR/assets/config/.codex" ]; then
        run cp -r "$MACHINE_DIR/assets/config/.codex" "$FULL_PATH/.codex"
    fi
else
    echo -e "${GREEN}[2/9] 跳过 .codex/ 配置${NC}"
fi

# ── [3/9] 复制 Skills ───────────────────────────────────────
echo -e "${GREEN}[3/9] 复制 Skills...${NC}"
run mkdir -p "$FULL_PATH/.skills"
IFS=',' read -ra SKILLS <<< "$SKILLS_LIST"
SKILL_COUNT=0
for skill in "${SKILLS[@]}"; do
    skill=$(echo "$skill" | xargs)
    src="$MACHINE_DIR/assets/skills/$skill"
    if [ -d "$src" ]; then
        run cp -r "$src" "$FULL_PATH/.skills/$skill"
        echo -e "  ${GREEN}✓${NC} $skill"
        ((SKILL_COUNT++)) || true
    else
        echo -e "  ${YELLOW}⚠${NC} 技能不存在: $skill（跳过）"
    fi
done

# ── [4/9] 复制工作流 ────────────────────────────────────────
if $WITH_WORKFLOW; then
    echo -e "${GREEN}[4/9] 复制开发工作流...${NC}"
    run mkdir -p "$FULL_PATH/.workflow"
    if [ -d "$MACHINE_DIR/assets/workflow/auto-dev-loop" ]; then
        run cp -r "$MACHINE_DIR/assets/workflow/auto-dev-loop" "$FULL_PATH/.workflow/auto-dev-loop"
        echo -e "  ${GREEN}✓${NC} auto-dev-loop（需求→计划→实施→验证→迭代）"
    fi
    if [ -d "$MACHINE_DIR/assets/workflow/canvas-dev" ]; then
        run cp -r "$MACHINE_DIR/assets/workflow/canvas-dev" "$FULL_PATH/.workflow/canvas-dev"
        echo -e "  ${GREEN}✓${NC} canvas-dev（白板驱动开发）"
    fi
else
    echo -e "${GREEN}[4/9] 跳过工作流${NC}"
fi

# ── [5/9] 复制参考文档（方法论 + 案例 + 提示词 + 指南）─────
if ! $NO_DOCS; then
    echo -e "${GREEN}[5/9] 复制参考文档...${NC}"
    run mkdir -p "$FULL_PATH/docs/reference"

    # 方法论文档（核心理念、架构原则、开发经验）
    if [ -d "$MACHINE_DIR/assets/documents/principles" ]; then
        run cp -r "$MACHINE_DIR/assets/documents/principles" "$FULL_PATH/docs/reference/principles"
        echo -e "  ${GREEN}✓${NC} principles/（核心理念 + 架构原则 + 开发经验）"
    fi

    # 案例研究（真实项目开发过程）
    if [ -d "$MACHINE_DIR/assets/documents/case-studies" ]; then
        run cp -r "$MACHINE_DIR/assets/documents/case-studies" "$FULL_PATH/docs/reference/case-studies"
        echo -e "  ${GREEN}✓${NC} case-studies/（真实项目案例）"
    fi

    # 入门指南
    if [ -d "$MACHINE_DIR/assets/documents/guides" ]; then
        run cp -r "$MACHINE_DIR/assets/documents/guides" "$FULL_PATH/docs/reference/guides"
        echo -e "  ${GREEN}✓${NC} guides/（入门指南 + 方法手册）"
    fi

    # 提示词库
    if [ -d "$MACHINE_DIR/assets/prompts" ]; then
        run cp -r "$MACHINE_DIR/assets/prompts" "$FULL_PATH/docs/reference/prompts"
        echo -e "  ${GREEN}✓${NC} prompts/（编程提示词库）"
    fi

    # 入门文档
    if [ -d "$MACHINE_DIR/docs/onboarding" ]; then
        run cp -r "$MACHINE_DIR/docs/onboarding" "$FULL_PATH/docs/reference/onboarding"
        echo -e "  ${GREEN}✓${NC} onboarding/（孵化指南 + 分步指南）"
    fi

    # 技能选择器脚本
    if [ -d "$MACHINE_DIR/assets/scripts" ]; then
        run mkdir -p "$FULL_PATH/scripts"
        run cp "$MACHINE_DIR/assets/scripts/skill-picker.py" "$FULL_PATH/scripts/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} skill-picker.py（技能推荐工具）"
    fi
else
    echo -e "${GREEN}[5/9] 跳过参考文档${NC}"
fi

# ── [6/9] 创建项目定义模板 ──────────────────────────────────
echo -e "${GREEN}[6/9] 创建 docs/PROJECT_BRIEF.md...${NC}"
if ! $DRY_RUN; then
    cat > "$FULL_PATH/docs/PROJECT_BRIEF.md" << 'BRIEF_EOF'
# 项目定义 — PROJECT_BRIEF.md

> 请填写以下 4 个问题，帮助 AI 理解你的项目意图。
> 填写完成后，告诉 AI：「阅读 docs/PROJECT_BRIEF.md，然后开始开发」。

---

## 1. 目标：我要解决什么问题？

<!-- 用 1-3 句话描述你想做的事 -->


## 2. 现状：当前是什么情况？

<!-- 现在有什么？已经做了什么？ -->


## 3. 差距：从现状到目标，缺什么？

<!-- 技术？数据？接口？设计？ -->


## 4. 判断标准：怎么知道做完了？

<!-- 具体的验收条件，越明确越好 -->

---

## 参考资料

填写前，建议先看看：
- `docs/reference/principles/fundamentals/问题求解能力.md` — 学会定义问题
- `docs/reference/case-studies/` — 看别人怎么定义项目
- `docs/reference/guides/getting-started/` — 环境搭建指南

## 可用技能

运行 `ls .skills/` 查看已安装的技能。
运行 `python scripts/skill-picker.py --list` 查看所有可用技能。
BRIEF_EOF
    echo -e "  ${GREEN}✓${NC} docs/PROJECT_BRIEF.md"

    # 创建 TASKS.md 空模板
    cat > "$FULL_PATH/docs/TASKS.md" << 'TASKS_EOF'
# 任务清单

> 由 AI 根据 PROJECT_BRIEF.md 自动生成，每完成一个任务标记 [x]。

## 阶段 1：基础架构
<!-- AI 会在此处添加任务 -->

## 已完成
<!-- 完成的任务移到这里 -->
TASKS_EOF
    echo -e "  ${GREEN}✓${NC} docs/TASKS.md"

    # 创建 MEMORY.md 空模板
    cat > "$FULL_PATH/docs/MEMORY.md" << 'MEMORY_EOF'
# 项目记忆

> 记录架构决策、踩坑经验、关键上下文。AI 每次启动时读取此文件恢复记忆。

## 架构决策
<!-- 记录重要技术选型和原因 -->

## 踩坑记录
<!-- 记录遇到的问题和解决方案 -->

## 关键上下文
<!-- 项目的核心约束和目标 -->
MEMORY_EOF
    echo -e "  ${GREEN}✓${NC} docs/MEMORY.md"
else
    echo -e "  ${BLUE}[DRY]${NC} 创建 docs/PROJECT_BRIEF.md"
fi

# ── [7/9] 创建 README ───────────────────────────────────────
echo -e "${GREEN}[7/9] 创建 README.md...${NC}"
if ! $DRY_RUN; then
    cat > "$FULL_PATH/README.md" << README_EOF
# $PROJECT_NAME

> 由 vibe-coding-cn 母机孵化，$(date +%Y-%m-%d)

## 快速开始

1. 填写 \`docs/PROJECT_BRIEF.md\`（项目定义）
2. 告诉 AI：「阅读 docs/PROJECT_BRIEF.md，然后开始开发」

## 项目结构

\`\`\`
$PROJECT_NAME/
├── .skills/              # AI 领域技能（$SKILL_COUNT 个）
├── .workflow/             # 自动开发工作流
├── docs/
│   ├── PROJECT_BRIEF.md   # 📝 项目定义（待填写）
│   └── reference/         # 参考文档
│       ├── principles/    # 核心理念 + 架构原则
│       ├── case-studies/  # 真实项目案例
│       ├── guides/        # 入门指南
│       └── prompts/       # 编程提示词库
├── src/                   # 源代码
├── tests/                 # 测试
└── scripts/               # 工具脚本
\`\`\`

## 开发流程

\`\`\`
需求分析 → 实施计划 → 分步实现 → 验证测试 → 迭代
\`\`\`

参考：\`.workflow/auto-dev-loop/\`

## 技能列表

\`\`\`bash
ls .skills/
python scripts/skill-picker.py --list
\`\`\`
README_EOF
    echo -e "  ${GREEN}✓${NC} README.md"
else
    echo -e "  ${BLUE}[DRY]${NC} 创建 README.md"
fi

# ── [8/9] 生成 AI 助手入口文件 ──────────────────────────────
echo -e "${GREEN}[8/9] 生成 AI 助手入口文件...${NC}"
if $DRY_RUN; then
    case "$AI_TYPE" in
        claude)  echo -e "  ${BLUE}[DRY]${NC} 将生成 CLAUDE.md" ;;
        cursor)  echo -e "  ${BLUE}[DRY]${NC} 将生成 .cursorrules" ;;
        copilot) echo -e "  ${BLUE}[DRY]${NC} 将生成 .github/copilot-instructions.md" ;;
        windsurf) echo -e "  ${BLUE}[DRY]${NC} 将生成 .windsurfrules" ;;
        cline)   echo -e "  ${BLUE}[DRY]${NC} 将生成 .clinerules" ;;
        codex)   echo -e "  ${BLUE}[DRY]${NC} 将生成 AGENTS.md" ;;
        all)
            echo -e "  ${BLUE}[DRY]${NC} 将生成 CLAUDE.md"
            echo -e "  ${BLUE}[DRY]${NC} 将生成 .cursorrules"
            echo -e "  ${BLUE}[DRY]${NC} 将生成 .github/copilot-instructions.md"
            echo -e "  ${BLUE}[DRY]${NC} 将生成 .windsurfrules"
            echo -e "  ${BLUE}[DRY]${NC} 将生成 .clinerules"
            echo -e "  ${BLUE}[DRY]${NC} 将生成 AGENTS.md"
            ;;
    esac
else
    case "$AI_TYPE" in
        claude)  generate_claude_md "$FULL_PATH" "$SKILLS_LIST" "$MACHINE_DIR" ;;
        cursor)  generate_cursorrules "$FULL_PATH" "$SKILLS_LIST" ;;
        copilot) generate_copilot_instructions "$FULL_PATH" "$SKILLS_LIST" ;;
        windsurf) generate_windsurfrules "$FULL_PATH" "$SKILLS_LIST" ;;
        cline)   generate_clinerules "$FULL_PATH" "$SKILLS_LIST" ;;
        codex)   generate_agents_md "$FULL_PATH" "$SKILLS_LIST" "$MACHINE_DIR" ;;
        all)
            generate_claude_md "$FULL_PATH" "$SKILLS_LIST" "$MACHINE_DIR"
            generate_cursorrules "$FULL_PATH" "$SKILLS_LIST"
            generate_copilot_instructions "$FULL_PATH" "$SKILLS_LIST"
            generate_windsurfrules "$FULL_PATH" "$SKILLS_LIST"
            generate_clinerules "$FULL_PATH" "$SKILLS_LIST"
            if ! $NO_AGENTS; then
                generate_agents_md "$FULL_PATH" "$SKILLS_LIST" "$MACHINE_DIR"
            fi
            ;;
    esac
fi

# ── [9/9] 初始化 Git ────────────────────────────────────────
echo -e "${GREEN}[9/9] 初始化 Git...${NC}"
if ! $DRY_RUN; then
    if [ ! -d "$FULL_PATH/.git" ]; then
        (cd "$FULL_PATH" && git init -q && git add -A && git commit -q -m "init: vibe-init complete incubation" 2>/dev/null || true)
        echo -e "  ${GREEN}✓${NC} Git 仓库已初始化"
    else
        echo -e "  ${YELLOW}⚠${NC} Git 仓库已存在（跳过）"
    fi
else
    echo -e "  ${BLUE}[DRY]${NC} git init"
fi

# ── 完成 ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   ✅ 项目孵化完成！                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}📁 项目目录:${NC}  $FULL_PATH"
echo ""
echo -e "  ${YELLOW}📦 已就绪:${NC}"
echo -e "    🔧 .skills/          — $SKILL_COUNT 个领域技能"
echo -e "    🔄 .workflow/        — 自动开发工作流（5 步闭环）"
echo -e "    📋 PROJECT_BRIEF.md  — 项目定义模板（待填写）"
echo -e "    📖 docs/reference/   — 方法论 + 案例 + 提示词 + 指南"
echo -e "    📂 src/ + tests/     — 代码骨架"
echo ""
echo -e "  ${YELLOW}🚀 下一步:${NC}"
echo -e "    1. ${GREEN}cd $FULL_PATH${NC}"
echo -e "    2. 编辑 ${GREEN}docs/PROJECT_BRIEF.md${NC}，填写项目定义"
echo -e "    3. 告诉 AI：「阅读 docs/PROJECT_BRIEF.md，然后开始开发」"
echo ""

case "$AI_TYPE" in
    claude)  echo -e "  ${YELLOW}启动:${NC}  cd $FULL_PATH && claude" ;;
    cursor)  echo -e "  ${YELLOW}启动:${NC}  用 Cursor 打开 $FULL_PATH" ;;
    copilot) echo -e "  ${YELLOW}启动:${NC}  用 VS Code 打开 $FULL_PATH（Copilot 自动加载）" ;;
    windsurf) echo -e "  ${YELLOW}启动:${NC}  用 Windsurf 打开 $FULL_PATH" ;;
    cline)   echo -e "  ${YELLOW}启动:${NC}  用 VS Code + Cline 扩展打开 $FULL_PATH" ;;
    codex)   echo -e "  ${YELLOW}启动:${NC}  cd $FULL_PATH && codex" ;;
    all)
        echo -e "  ${YELLOW}启动:${NC}"
        echo -e "    Claude:  cd $FULL_PATH && claude"
        echo -e "    Cursor:  用 Cursor 打开 $FULL_PATH"
        echo -e "    Copilot: 用 VS Code 打开 $FULL_PATH"
        echo -e "    Codex:   cd $FULL_PATH && codex"
        ;;
esac
echo ""
