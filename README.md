# Cognix

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.10-green.svg)]()

非侵入式记忆引擎，为 AI Agent 提供长期记忆、短期上下文、工作习惯理解、流程复用与主动提醒能力。面向飞书办公场景的外挂式记忆系统，让 AI 助手越用越懂用户、越用越会做事。

## 更新日志

- 🧠 **偏好记忆**：自动记住用户长期办公偏好（文档格式、汇报对象、习惯时间等），无需反复说明
- 🔍 **规律挖掘**：从 Shell 历史、飞书行为、日程数据中自动发现周期性工作习惯和规律
- ⏰ **主动服务**：在合适时机主动提醒、生成内容甚至执行重复性任务，减少手动操作
- 🔄 **动态适配**：根据用户行为变化自动调整记忆和规则，适应工作模式的演进
- 📝 **可解释性**：所有记忆和规则都清晰可见，支持手动编辑和确认，避免黑盒问题
- 🤖 **多入口支持**：同时提供 CLI 工具和飞书 Bot 两种交互方式，适配不同使用场景
- ⚡ **轻量化设计**：基于 SQLite + 文件存储，无需外部数据库，开箱即用
- ✅ **【新增】可编辑记忆**：所有偏好和规则以Markdown文件存储，支持直接手动编辑，零学习成本修改记忆
- ✅ **【新增】偏好体系**：8大类30+细分偏好配置，覆盖所有办公场景个性化需求

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

## 🛠️ 技术栈

- **核心开发**：Python 3.10+
- **CLI 框架**：Click
- **任务调度**：APScheduler
- **飞书接入**：lark-oapi-sdk
- ~~**持久化存储**：SQLite + JSON 文件~~
- **【修改】持久化存储**：Markdown（真相源） + SQLite（索引层） + JSONL（事件日志）
- **AI 集成**：LangChain 生态（可对接任意大模型）
- **无外部依赖**：无需部署 Redis、MySQL 等服务，开箱即用

## 🚀 快速开始

### 环境要求

- Python >= 3.10
- Redis >= 6.0（可选，用于短期记忆高可用）

### 安装

```bash
pip install cognix
```

### 基础配置

```bash
# 初始化配置
cognix init

# 配置飞书 Bot（可选，需要飞书开发者权限）
cognix config set feishu_app_id "cli_xxxxxx"
cognix config set feishu_app_secret "xxxxxx"
cognix config set feishu_chat_id "oc_xxxxxx"

# 配置个人偏好
cognix config set report_format "markdown"
cognix config set weekly_report_time "周五 18:00"
cognix config set weekly_report_receiver "张三,李四"

# 【新增】直接编辑Markdown文件配置
# 打开偏好配置文件：~/.cognix/memory/preferences.md
# 打开规则配置文件：~/.cognix/memory/rules.md
# 保存后自动生效，无需重启服务
```

### 核心功能使用

```bash
# 1. 创建周报自动生成规则
cognix rule create-weekly
# 确认规则生效
cognix rule confirm 1

# 2. 查看所有规则
cognix rule list

# 3. 启动后台服务
cognix start

# 4. 查看服务状态
cognix status

# 5. 手动触发周报生成
cognix suggest generate-weekly

# 6. 生成周报统计
cognix weekly-report

# 【新增】偏好管理命令
cognix config list --all # 查看所有偏好及说明
cognix config export preferences.md # 导出偏好配置
cognix config import preferences.md # 导入偏好配置
cognix config reset # 重置所有偏好为默认值
```

## 📚 功能介绍

### 记忆管理
Cognix 会自动采集和学习以下行为数据：
- Shell 命令执行历史
- 飞书日程、消息、文档访问记录
- 手动上报的偏好和事件
- 规则执行的反馈结果

【新增记忆结构】：
- **短期记忆**：JSONL格式存储事件日志，按天滚动
- **中期记忆**：Markdown格式存储用户偏好，支持手动编辑
- **长期记忆**：Markdown格式存储自动化规则和知识
- **索引层**：SQLite自动同步Markdown内容，提供高性能查询

【📌 双向存储设计理念】：
- ✅ **零门槛操作**：所有配置以纯Markdown存储，用户可直接编辑，无需学习命令
- ⚡ **高性能查询**：SQLite作为索引层，提供毫秒级查询性能，避免全量解析Markdown
- 🔒 **数据永不丢失**：Markdown为唯一真相源，SQLite可随时重建，天然备份
- 📦 **迁移零成本**：纯文本格式永久兼容，复制文件即可完成迁移/备份

### 规则引擎
系统支持以下规则类型：
- 时间触发规则：固定时间执行特定动作
- 事件触发规则：特定事件发生时执行动作
- 条件触发规则：满足特定条件时自动触发

### 主动交互
支持多种主动提醒方式：
- CLI 桌面通知
- 飞书消息通知
- 飞书交互式卡片
- 自动生成内容并发送

### 【新增】偏好管理
Cognix提供8大类30+细分偏好配置：
- 基础配置：语言、时区、免打扰等
- 内容生成偏好：格式、风格、长度等
- 场景化偏好：周报、会议等场景专属配置
- 通知偏好：渠道、时间、级别等
- 隐私配置：数据采集、敏感信息过滤等

## 📖 文档索引

- [需求文档](./docs/需求文档.md)
- [产品需求文档(PRD)](./docs/PRD.md)
- [实现计划](./docs/实现计划.md)
- [API 文档](./docs/API文档.md)
- [开发指南](./docs/开发指南.md)
- 【新增】[记忆格式说明](./docs/记忆格式说明.md)
- 【新增】[偏好配置手册](./docs/偏好配置手册.md)

## 👨‍💻 开发指南

### 本地开发

```bash
# 克隆项目
git clone https://github.com/your-org/cognix.git
cd cognix

# 安装依赖
pip install -r requirements.txt

# 安装为开发模式
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
├── core/              # 核心业务模块
│   ├── preference_store.py    # 偏好存储
│   ├── rule_engine.py         # 规则引擎
│   ├── scheduler.py           # 任务调度
│   └── event_collector.py     # 事件采集与学习
├── storage/           # 存储层
│   ├── sqlite_store.py        # SQLite 索引存储
│   ├── file_store.py          # JSONL 事件存储
│   └── markdown_store.py      # 【新增】Markdown 记忆存储
├── interfaces/        # 交互层
│   ├── cli/                 # CLI 工具
│   └── feishu/              # 飞书 Bot
└── utils/             # 工具函数
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
