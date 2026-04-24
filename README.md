# Cognix

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.10-green.svg)]()
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

面向企业办公场景的主动式个人工作习惯记忆引擎，核心价值是主动理解用户工作模式，在正确时间提供正确帮助，让 AI 真正适配人的工作习惯，而不是让人适配 AI。

## ✨ 核心特性

- 🧠 **偏好记忆**：自动记住用户长期办公偏好（文档格式、汇报对象、习惯时间等），无需反复说明
- 🔍 **规律挖掘**：从 Shell 历史、飞书行为、日程数据中自动发现周期性工作习惯和规律
- ⏰ **主动服务**：在合适时机主动提醒、生成内容甚至执行重复性任务，减少手动操作
- 🔄 **动态适配**：根据用户行为变化自动调整记忆和规则，适应工作模式的演进
- 📝 **可解释性**：所有记忆和规则都清晰可见，支持手动编辑和确认，避免黑盒问题
- 🤖 **多入口支持**：同时提供 CLI 工具和飞书 Bot 两种交互方式，适配不同使用场景
- ⚡ **轻量化设计**：基于 SQLite + 文件存储，无需外部数据库，开箱即用
- ✅ **【新增】可编辑记忆**：所有偏好和规则以Markdown文件存储，支持直接手动编辑，零学习成本修改记忆
- ✅ **【新增】偏好体系**：8大类30+细分偏好配置，覆盖所有办公场景个性化需求

## 🎯 应用场景

- **自动周报生成**：每周五自动汇总一周工作内容，生成符合你习惯格式的周报
- **会议准备提醒**：会议前 10 分钟自动拉取相关文档，提醒你准备相关材料
- **重复任务自动化**：识别周期性重复操作，生成自动化规则，一键执行
- **工作习惯优化**：分析工作时间分布，给出合理的时间管理建议
- **个性化 AI 助手**：为上层 AI Agent 提供个人记忆能力，让助手更懂你

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
- pip 包管理器

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

# 运行测试
pytest tests/
```

### 项目结构

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

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 📄 许可证

本项目采用 [MIT](./LICENSE) 许可证。
