# Cognix

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.10-green.svg)]()

非侵入式记忆引擎，为 AI Agent 提供长期记忆、短期上下文、工作习惯理解、流程复用与主动提醒能力。面向飞书办公场景的外挂式记忆系统，让 AI 助手越用越懂用户、越用越会做事。

## 更新日志

### 2026-04-27
- ✅ **OpenClaw 插件接入测试完成**
  - 新增 `openclaw-plugin-cognix/` 目录，包含 TypeScript 插件实现
  - 支持 `memory_search`、`memory_store`、`memory_get`、`memory_list`、`memory_forget` 5 个工具
  - 支持 auto-capture（自动存储对话）和 auto-recall（自动注入记忆）

## 特性

- **五层架构**：数据接入层 → 短期记忆层 → 长期记忆层 → 智能决策层 → 服务执行层
- **Markdown 持久化存储**：5 类长期记忆分类存储（user/settings/office/feedback/reference），可读可编辑可迁移
- **SQLite FTS5 全文检索**：轻量本地检索，无需向量数据库
- **Redis 短期记忆 + 内存回退**：高可用短期存储，支持 TTL 自动过期，Redis 不可用时自动回退内存
- **事件总线**：统一多源数据接入入口，发布/订阅模式
- **记忆压缩流水线**：自动提取高价值信息，避免记忆污染
- **双轨检索机制**：固定核心记忆注入 + 动态相关记忆召回
- **工作流沉淀**：自动识别重复行为，沉淀可复用工作流
- **主动提醒服务**：支持多周期定时触发，飞书卡片交互（待集成）
- **100% 向下兼容**：所有旧接口保持可用，渐进式升级

## 快速开始

### 环境要求

- Python >= 3.10
- Redis >= 6.0（可选，用于短期记忆高可用）

### 安装

```bash
pip install -e .
pip install redis  # 可选
```

### 核心模块使用

```python
from cognix.core.memory_system import get_memory_system
from cognix.core.memory_compressor import get_memory_compressor
from cognix.core.retrieval_engine import get_retrieval_engine
from cognix.core.event_bus import get_global_event_bus, Event
from cognix.core.skills_manager import get_skills_manager
from cognix.core.reminder_service import get_reminder_service
from datetime import datetime

# 1. 记忆分类存储
memory = get_memory_system()
memory.add_classified_memory("office", "周报", "每周五下午5点发周报")
memory.add_classified_memory("user", "用户信息", "姓名：张三")

# 2. 记忆压缩与自动分类
compressor = get_memory_compressor()
session = "用户：以后回答先给结论，少用表格"
result = compressor.compress_session(session)

# 3. 双轨检索增强
engine = get_retrieval_engine()
context = engine.build_context("帮我写周报")
enhanced_prompt = engine.enhance_prompt("请帮我完成任务", "周报")

# 4. 事件总线
bus = get_global_event_bus()
def handler(e): print(f"收到事件: {e.content}")
bus.subscribe("feishu_message", handler)
bus.publish(Event(
    user_id="u001",
    time=datetime.now(),
    source="feishu",
    event_type="feishu_message",
    content="帮我生成周报",
    metadata={}
))

# 5. 工作流沉淀
sm = get_skills_manager()
sm.create_skill(
    name="weekly_report",
    description="每周五生成周报",
    trigger="friday_17_00",
    steps=["收集数据", "生成报告", "发送给经理"]
)

# 6. 主动提醒
rs = get_reminder_service()
rs.add_reminder(
    name="周报提醒",
    trigger="friday_17_00",
    description="每周五下午5点发周报",
    action="send_weekly_report"
)
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
┌─────────────────────────────────────────────────────────────┐
│                     数据接入层                               │
│  事件总线 (Event Bus) → 多源数据标准化接入                   │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     短期记忆层                               │
│  Redis Hash 存储 + 内存回退 → TTL 自动过期                   │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     长期记忆层                               │
│  Markdown 分类存储 (5类) + SQLite FTS5 全文检索              │
│  user / settings / office / feedback / reference            │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     智能决策层                               │
│  记忆压缩流水线 → 自动分类 → 关键信息提取                    │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     服务执行层                               │
│  双轨检索 │ 工作流沉淀 │ 主动提醒 │ 飞书卡片交互（待集成）   │
└─────────────────────────────────────────────────────────────┘
```

详细架构说明请参考 [架构文档](./docs/architecture.md)。

## 项目结构

```
cognix/
├── core/                          # 核心业务模块
│   ├── memory_system.py           # 记忆系统核心（兼容旧接口）
│   ├── memory_classifier.py       # 长期记忆分类存储（5类）
│   ├── memory_compressor.py       # 记忆压缩与自动分类
│   ├── short_term_redis.py        # Redis 短期记忆 + 内存回退
│   ├── retrieval_engine.py        # 双轨检索引擎（固定+动态）
│   ├── event_bus.py               # 事件总线（发布/订阅）
│   ├── skills_manager.py          # 工作流沉淀与技能管理
│   ├── reminder_service.py        # 主动提醒服务
│   ├── preference_store.py        # 偏好存储（旧）
│   ├── compressor.py              # 短期记忆压缩（旧）
│   ├── deduplicator.py            # 记忆去重（旧）
│   └── conflict_resolver.py       # 冲突解决（旧）
├── hooks/                         # 事件监听（旧）
│   ├── base.py
│   ├── feishu_hook.py
│   └── context_threshold.py
├── dream/                         # 定时整理（旧）
│   └── scheduler.py
├── interfaces/                    # 交互层
│   ├── agent/                     # Agent 接口
│   ├── cli/                       # CLI 工具
│   └── feishu/                    # 飞书集成
├── storage/                       # 存储层
│   └── sqlite_store.py
└── utils/                         # 工具函数
    └── config.py
skills/
└── cognix-memory.yaml             # OpenClaw Skill 描述
```

## 文档索引

- [架构说明](./docs/architecture.md)
- [手动测试指南](./docs/manual-testing-guide.md)
- [CLI 使用指南](./docs/cli-guide.md)
- [飞书集成指南](./docs/feishu-integration.md)
- [完整设计文档](./docs/superpowers/specs/2026-04-26-memory-engine-full-implementation-design.md)
- [实现计划](./docs/superpowers/plans/2026-04-26-memory-engine-implementation-plan.md)
- [废弃文档归档](./docs/archive/)

## 测试

### 运行测试

```bash
# 完整测试套件（Redis 未启动时自动跳过相关测试）
pytest tests/ -v

# 仅核心模块测试
pytest tests/test_event_bus.py tests/test_memory_classifier.py tests/test_memory_compressor.py tests/test_retrieval_engine.py tests/test_skills_manager.py tests/test_reminder_service.py -v

# 启动 Redis 后运行完整短期记忆测试
pytest tests/test_short_term_redis.py -v
```

### 测试覆盖率

```bash
pip install pytest-cov
pytest tests/ --cov=cognix.core --cov-report=term-missing
```

详细测试说明请参考 [手动测试指南](./docs/manual-testing-guide.md)。

## 本地开发

```bash
git clone https://github.com/Starnever0/Cognix.git
cd Cognix
pip install -e .
pytest tests/
```

## 许可证

[MIT](./LICENSE)
