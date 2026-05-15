# .

> 由 vibe-coding-cn 母机孵化，2026-05-15

## 快速开始

1. 填写 `docs/PROJECT_BRIEF.md`（项目定义）
2. 告诉 AI：「阅读 docs/PROJECT_BRIEF.md，然后开始开发」

## 项目结构

```
./
├── .skills/              # AI 领域技能（12 个）
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
```

## 开发流程

```
需求分析 → 实施计划 → 分步实现 → 验证测试 → 迭代
```

参考：`.workflow/auto-dev-loop/`

## 技能列表

```bash
ls .skills/
python scripts/skill-picker.py --list
```
