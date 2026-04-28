# Cognix 飞书记忆系统集成设计

## 概述

Cognix 是非侵入式记忆系统，任何 Agent 系统可通过 CLI 命令 + Skill 描述文件无冲突调用。本设计实现 Cognix 接入飞书 OpenClaw Agent，作为其记忆后端自动记录用户交互信息、整理习惯偏好。

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

## MVP 功能范围

### 1. CLI 命令（非侵入式接口）

Agent 通过 shell 调用 CLI 命令与记忆系统交互：

| 命令 | 功能 | 输出 |
|------|------|------|
| `cognix remember <heading> <content>` | 记录记忆 | 记忆ID |
| `cognix recall <query>` | 搜索记忆 | 匹配的记忆列表(JSON) |
| `cognix context [--days N]` | 获取近期上下文 | 上下文文本 |
| `cognix autodream` | 手动触发记忆整理 | 整理报告 |
| `cognix serve` | 启动后台服务 | 服务状态 |

### 2. 飞书消息 Hook

- 监听飞书消息事件，自动将对话内容记录到短期记忆
- 当短期记忆达到阈值，自动压缩为持久记忆

### 3. 短期记忆压缩

- 会话上下文超过阈值时，自动提取关键信息压缩为长期记忆
- 保留摘要作为持久会话记忆

### 4. Autodream 定时整理

- 每24小时自动运行
- 记忆去重、冲突解决
- 从交互记录中提取用户偏好
- 整理偏好到 preference_store

### 5. OpenClaw Skill 描述文件

- YAML 格式 Skill 描述，让 OpenClaw Agent 知道何时及如何调用 Cognix

## 数据流

```
飞书消息 → Hook捕获 → 短期记忆(session)
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

## 文件结构（解耦版）

```
cognix/
├── __init__.py
├── core/
│   ├── memory_system.py          # 已有：Markdown+SQLite记忆核心
│   ├── preference_store.py       # 已有：偏好存储
│   ├── compressor.py             # 新增：短期记忆压缩策略
│   ├── deduplicator.py           # 新增：记忆去重
│   ├── conflict_resolver.py      # 新增：记忆冲突解决
│   └── preference_extractor.py   # 新增：从交互中提取偏好
├── hooks/
│   ├── __init__.py               # Hook注册与调度
│   ├── base.py                   # Hook基类
│   ├── feishu_hook.py            # 飞书消息Hook
│   └── context_threshold.py      # 上下文阈值触发器
├── dream/
│   ├── __init__.py               # Autodream调度
│   └── scheduler.py              # 定时任务调度器
├── interfaces/
│   ├── agent/
│   │   └── __init__.py           # 已有：AgentMemoryClient
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py               # CLI入口
│   │   ├── cmd_remember.py       # remember子命令
│   │   ├── cmd_recall.py         # recall子命令
│   │   ├── cmd_context.py        # context子命令
│   │   ├── cmd_dream.py          # autodream子命令
│   │   └── cmd_serve.py          # serve子命令
│   └── feishu/
│       ├── __init__.py
│       ├── client.py             # 飞书API客户端
│       └── event_handler.py      # 飞书事件处理
├── storage/
│   ├── sqlite_store.py           # 已有
│   └── markdown_store.py         # 已有
└── utils/
    └── config.py                 # 已有
skills/
└── cognix-memory.yaml            # OpenClaw Skill描述
```

## 模块职责

### core/ — 核心处理逻辑

| 文件 | 职责 | 依赖 |
|------|------|------|
| `memory_system.py` | Markdown+SQLite记忆核心，CRUD操作 | config, sqlite3 |
| `preference_store.py` | 偏好存储与查询 | sqlite_store |
| `compressor.py` | 短期记忆压缩策略：提取关键信息，生成摘要 | memory_system |
| `deduplicator.py` | 记忆去重：基于内容相似度检测重复记忆 | memory_system |
| `conflict_resolver.py` | 冲突解决：检测矛盾记忆，标记待确认 | memory_system |
| `preference_extractor.py` | 偏好提取：从交互记录中识别用户习惯 | memory_system, preference_store |

### hooks/ — 事件监听

| 文件 | 职责 | 依赖 |
|------|------|------|
| `base.py` | Hook基类，定义on_event接口 | 无 |
| `feishu_hook.py` | 飞书消息监听，自动记录对话 | base, memory_system |
| `context_threshold.py` | 上下文阈值监控，触发压缩 | base, compressor |

### dream/ — 定时整理

| 文件 | 职责 | 依赖 |
|------|------|------|
| `scheduler.py` | 定时任务调度，协调去重/冲突解决/偏好提取 | deduplicator, conflict_resolver, preference_extractor |

### interfaces/cli/ — CLI接口

| 文件 | 职责 | 依赖 |
|------|------|------|
| `main.py` | CLI入口，注册子命令 | click |
| `cmd_remember.py` | remember子命令 | memory_system |
| `cmd_recall.py` | recall子命令 | memory_system |
| `cmd_context.py` | context子命令 | memory_system |
| `cmd_dream.py` | autodream子命令 | dream.scheduler |
| `cmd_serve.py` | serve子命令，启动后台服务 | hooks, dream |

### interfaces/feishu/ — 飞书集成

| 文件 | 职责 | 依赖 |
|------|------|------|
| `client.py` | 飞书API封装（发送消息、验证事件） | lark-oapi |
| `event_handler.py` | 飞书事件路由与处理 | client, hooks |

## 关键接口定义

### Hook基类

```python
class BaseHook:
    def on_event(self, event_type: str, data: dict) -> None:
        raise NotImplementedError
```

### Compressor

```python
class MemoryCompressor:
    def should_compress(self, session_id: str) -> bool:
        """检查是否需要压缩"""
    def compress(self, session_id: str) -> dict:
        """执行压缩，返回压缩结果"""
```

### Deduplicator

```python
class MemoryDeduplicator:
    def find_duplicates(self, source: str = None) -> list:
        """查找重复记忆"""
    def merge_duplicates(self, duplicate_ids: list) -> str:
        """合并重复记忆，返回保留的记忆ID"""
```

### PreferenceExtractor

```python
class PreferenceExtractor:
    def extract_from_interactions(self, days: int = 7) -> list:
        """从交互记录中提取偏好"""
    def save_preferences(self, preferences: list) -> int:
        """保存提取的偏好，返回保存数量"""
```

### Autodream Scheduler

```python
class AutodreamScheduler:
    def run_once(self) -> dict:
        """执行一次完整整理"""
    def start(self, interval_hours: int = 24):
        """启动定时整理"""
    def stop(self):
        """停止定时整理"""
```

## 实现优先级

1. **Phase 1**: CLI命令 + Skill描述文件（让Agent可以调用）
2. **Phase 2**: 飞书Hook + 事件处理（自动记录对话）
3. **Phase 3**: 短期记忆压缩（上下文管理）
4. **Phase 4**: Autodream定时整理（去重/冲突/偏好提取）
