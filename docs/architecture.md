# Cognix 架构说明

## 设计理念

Cognix 是非侵入式记忆系统，核心设计原则：

1. **非侵入**：Agent 通过 CLI 命令和 Skill 描述文件调用，不需要修改 Agent 代码
2. **解耦**：每个功能模块独立文件，职责单一，可独立测试和替换
3. **Markdown 优先**：Markdown 是记忆的真实来源，SQLite 是索引，人类可直接阅读和编辑 Markdown 文件
4. **自动整理**：Autodream 机制定期去重、解决冲突、提取偏好，保持记忆系统健康

## 系统架构

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
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │   │
│  │  │ 短期记忆  │ │ 每日记忆  │ │ 持久记忆(MEMORY) │  │   │
│  │  │ (会话级)  │ │ (Markdown)│ │ (Markdown+SQLite)│  │   │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │   │
│  │  ┌──────────────────────────────────────────────┐│   │
│  │  │  FTS5 全文索引 + 偏好存储 + 规则引擎          ││   │
│  │  └──────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## 记忆层级

Cognix 采用三级记忆架构，模拟人类记忆模型：

### 短期记忆（Session）

- **存储位置**：内存（`short_term_memory` 字典）
- **生命周期**：会话期间，会话结束即清除
- **用途**：当前对话的上下文信息
- **触发压缩**：当短期记忆条目达到阈值（默认 50 条），自动压缩为长期记忆

### 每日记忆（Daily）

- **存储位置**：`~/.cognix/memory/YYYY-MM-DD.md`
- **生命周期**：按天归档，永久保留
- **用途**：每天的工作日志和交互记录
- **格式**：Markdown，以 `## 标题` 分块

### 持久记忆（Persistent）

- **存储位置**：`~/.cognix/MEMORY.md`
- **生命周期**：永久保留，跨会话可用
- **用途**：用户长期偏好、重要决策、关键信息
- **格式**：Markdown，与每日记忆格式一致

## 数据流

```
飞书消息 → Hook 捕获 → 短期记忆(session)
                              │
                        达到阈值触发压缩
                              │
                              ▼
                提取关键信息 → 每日记忆(Markdown) + 持久记忆
                              │
                        Autodream 定时整理
                              │
                              ▼
                去重/冲突解决/偏好提取 → preference_store
```

## 模块说明

### core/ — 核心处理逻辑

| 模块 | 职责 | 关键接口 |
|------|------|---------|
| `memory_system.py` | Markdown + SQLite 记忆核心 | `add_memory()`, `search_memory()`, `get_daily_context()` |
| `preference_store.py` | 偏好存储与查询 | `set()`, `get()`, `list()` |
| `compressor.py` | 短期记忆压缩 | `should_compress()`, `compress()` |
| `deduplicator.py` | 记忆去重 | `find_duplicates()`, `merge_duplicates()` |
| `conflict_resolver.py` | 冲突解决 | `find_conflicts()`, `resolve_conflict()` |
| `preference_extractor.py` | 偏好提取 | `extract_from_interactions()`, `save_preferences()` |

### hooks/ — 事件监听

| 模块 | 职责 | 触发条件 |
|------|------|---------|
| `base.py` | Hook 基类 | — |
| `feishu_hook.py` | 飞书消息监听 | `feishu_message` 事件 |
| `context_threshold.py` | 上下文阈值监控 | `short_term_add` 事件，条目 >= 50 |

Hook 系统通过 `HookRegistry` 统一管理，支持动态注册和事件分发。

### dream/ — 定时整理

| 模块 | 职责 |
|------|------|
| `scheduler.py` | Autodream 调度器，协调去重/冲突解决/偏好提取 |

Autodream 执行流程：

1. **去重**：扫描记忆，基于 Jaccard 相似度检测重复（阈值 0.85）
2. **冲突解决**：检测矛盾偏好（如"喜欢"与"不喜欢"同一事物），标记待确认
3. **偏好提取**：从交互记录中识别用户习惯关键词，保存到 preference_store

### interfaces/ — 交互层

| 模块 | 职责 |
|------|------|
| `cli/main.py` | CLI 入口，注册子命令 |
| `cli/cmd_*.py` | 各子命令实现 |
| `feishu/client.py` | 飞书 API 封装（消息发送、事件验证） |
| `feishu/event_handler.py` | 飞书事件路由，分发到 Hook 系统 |
| `agent/__init__.py` | AgentMemoryClient 接口 |

### storage/ — 存储层

| 模块 | 职责 |
|------|------|
| `sqlite_store.py` | SQLite 存储（偏好表 + 规则表） |
| `markdown_store.py` | Markdown 文件读写 |

## 存储结构

```
~/.cognix/
├── cognix.db                  # SQLite 数据库
│   ├── files                  # 文件元数据表
│   ├── chunks                 # 记忆块表
│   ├── chunks_fts             # FTS5 全文索引
│   ├── preferences            # 偏好表
│   └── rules                  # 规则表
├── memory/
│   ├── 2026-04-24.md          # 每日记忆
│   ├── 2026-04-25.md
│   └── ...
├── sessions/                  # 会话数据
├── events/                    # 事件日志
├── MEMORY.md                  # 持久记忆
└── .env                       # 配置文件
```

## 配置项

通过 `~/.cognix/.env` 管理：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FEISHU_APP_ID` | 飞书应用 ID | 空（不启用飞书 Hook） |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 空 |
| `LLM_BASE_URL` | LLM API 地址 | 空 |
| `LLM_API_KEY` | LLM API 密钥 | 空 |
| `LLM_MODEL` | LLM 模型名称 | `qwen3.5-35b` |
