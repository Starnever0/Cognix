# Cognix

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.10-green.svg)]()

非侵入式记忆系统，为 AI Agent 提供记忆存取能力。任何 Agent 系统都可以通过 CLI 命令 + Skill 描述文件无冲突调用，让 Agent 真正记住用户的交互信息与习惯偏好。

## 特性

- **非侵入式设计**：通过 CLI 命令和 Skill 描述文件接入，不侵入 Agent 内部逻辑
- **多级记忆**：短期记忆（会话级）、每日记忆（Markdown）、持久记忆（MEMORY.md），自动管理生命周期
- **FTS5 全文搜索**：基于 SQLite FTS5 的高效记忆检索
- **飞书集成**：监听飞书消息事件，自动记录对话到记忆系统
- **短期记忆压缩**：上下文达到阈值时自动压缩为长期记忆
- **Autodream 定时整理**：每 24 小时自动去重、解决冲突、提取偏好
- **OpenClaw Skill**：提供 YAML 格式 Skill 描述，飞书 OpenClaw Agent 可直接调用
- **Markdown + SQLite 双存储**：Markdown 是真实来源，SQLite 是索引，人类可读且高效检索

## 快速开始

### 环境要求

- Python >= 3.10

### 安装

```bash
pip install cognix
```

### CLI 命令

```bash
# 记录一条记忆
cognix remember "用户偏好" "用户喜欢用表格格式查看周报"

# 记录持久记忆（跨会话保留）
cognix remember "重要决策" "Q2 目标重点在用户增长" --persistent

# 搜索记忆
cognix recall "周报"

# 搜索持久记忆
cognix recall "偏好" --source persistent

# 获取近期上下文
cognix context --days 3

# 手动触发记忆整理
cognix dream

# 启动后台服务（Hook + 定时整理）
cognix serve --dream-interval 24
```

### 飞书 OpenClaw 集成

将 `skills/cognix-memory.yaml` 添加到 OpenClaw Agent 的 Skill 目录即可。Agent 会自动识别以下工具：

| 工具 | 用途 |
|------|------|
| `remember` | 记录用户的交互信息、偏好或重要事项 |
| `recall` | 搜索与关键词相关的历史信息 |
| `context` | 获取近期上下文，了解最近发生的事情 |
| `dream` | 手动触发记忆整理 |

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    飞书 OpenClaw Agent                    │
│  (通过 CLI 命令 + Skill 描述文件调用 Cognix)              │
└──────────────┬──────────────────────┬───────────────────┘
               │ CLI                  │ Skill
               ▼                      ▼
┌──────────────────────────────────────────────────────────┐
│                    Cognix 记忆系统                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  CLI 入口     │  │  飞书 Hook    │  │  Autodream    │  │
│  │  remember     │  │  消息监听     │  │  定时整理      │  │
│  │  recall       │  │  自动记录     │  │  压缩/去重     │  │
│  │  context      │  │              │  │  偏好提取      │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│         ▼                 ▼                   ▼          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            记忆核心 (memory_system.py)             │   │
│  │  短期记忆 → 每日记忆 → 持久记忆 → FTS5 索引       │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

详细架构说明请参考 [架构文档](./docs/architecture.md)。

## 项目结构

```
cognix/
├── core/                          # 核心业务模块
│   ├── memory_system.py           # Markdown + SQLite 记忆核心
│   ├── preference_store.py        # 偏好存储
│   ├── compressor.py              # 短期记忆压缩
│   ├── deduplicator.py            # 记忆去重
│   ├── conflict_resolver.py       # 冲突解决
│   └── preference_extractor.py    # 偏好提取
├── hooks/                         # 事件监听
│   ├── base.py                    # Hook 基类
│   ├── feishu_hook.py             # 飞书消息 Hook
│   └── context_threshold.py       # 上下文阈值触发器
├── dream/                         # 定时整理
│   └── scheduler.py               # Autodream 调度器
├── interfaces/                    # 交互层
│   ├── agent/                     # Agent 接口
│   ├── cli/                       # CLI 工具
│   │   ├── main.py                # CLI 入口
│   │   ├── cmd_remember.py        # remember 子命令
│   │   ├── cmd_recall.py          # recall 子命令
│   │   ├── cmd_context.py         # context 子命令
│   │   ├── cmd_dream.py           # dream 子命令
│   │   └── cmd_serve.py           # serve 子命令
│   └── feishu/                    # 飞书集成
│       ├── client.py              # 飞书 API 客户端
│       └── event_handler.py       # 飞书事件处理
├── storage/                       # 存储层
│   ├── sqlite_store.py            # SQLite 存储
│   └── markdown_store.py          # Markdown 存储
└── utils/                         # 工具函数
    └── config.py                  # 配置管理
skills/
└── cognix-memory.yaml             # OpenClaw Skill 描述
```

## 文档索引

- [架构说明](./docs/architecture.md)
- [CLI 使用指南](./docs/cli-guide.md)
- [飞书集成指南](./docs/feishu-integration.md)
- [设计文档](./docs/superpowers/specs/2026-04-25-feishu-memory-integration-design.md)

## 本地开发

```bash
git clone https://github.com/Starnever0/Cognix.git
cd Cognix
pip install -e .
pytest tests/
```

## 许可证

[MIT](./LICENSE)
