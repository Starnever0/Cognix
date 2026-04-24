# Cognix API 文档

## 概述

Cognix 提供三类对外接口：
- **CLI 命令行接口**：供用户直接在终端使用
- **Python SDK 接口**：供开发者在代码中集成 Cognix 能力
- **飞书事件接口**：供飞书 Bot 接收事件回调

所有接口遵循统一的错误码规范，返回格式清晰可扩展。

---

## 1. CLI 命令接口

### 1.1 全局命令

#### 初始化配置 / init
```bash
cognix init
```
**功能：** 初始化 Cognix 配置文件和数据库，首次使用必须执行
**参数：** 无
**示例：**
```bash
$ cognix init
✅ 配置文件已创建：~/.cognix/config.yaml
✅ 数据库已初始化：~/.cognix/cognix.db
✅ 事件存储目录已创建：~/.cognix/events/
```

#### 启动服务 / start
```bash
cognix start [--daemon]
```
**功能：** 启动 Cognix 后台服务，执行调度任务和主动提醒
**参数：**
- `--daemon`：可选，后台守护进程模式运行
**示例：**
```bash
# 前台运行
$ cognix start
🚀 Cognix 服务已启动，PID: 12345
📅 当前生效规则：3 个
🔔 监听端口：8765

# 后台运行
$ cognix start --daemon
✅ Cognix 后台服务已启动，PID: 12345
```

#### 查看服务状态 / status
```bash
cognix status
```
**功能：** 查看当前服务运行状态、生效规则、统计信息
**参数：** 无
**示例：**
```bash
$ cognix status
✅ 服务状态：运行中 (PID: 12345, 运行时间: 2天3小时)
📊 统计信息：
  - 总规则数：5 个（生效：4 个，待确认：1 个）
  - 已采集事件：1243 条
  - 已触发提醒：27 次
  - 周报生成：3 次
⏰ 下次任务：2024-05-24 18:00:00 - 生成周报
```

#### 停止服务 / stop
```bash
cognix stop
```
**功能：** 停止正在运行的 Cognix 服务
**参数：** 无
**示例：**
```bash
$ cognix stop
✅ Cognix 服务已停止
```

---

### 1.2 配置管理命令

#### 查看配置 / config list
```bash
cognix config list
```
**功能：** 查看所有当前配置项
**参数：** 无
**示例：**
```bash
$ cognix config list
📝 当前配置：
  report_format: markdown
  weekly_report_time: 周五 18:00
  weekly_report_receiver: 张三,李四
  feishu_app_id: cli_xxxxxx
  feishu_chat_id: oc_xxxxxx
```

#### 设置配置项 / config set
```bash
cognix config set <key> <value>
```
**功能：** 设置单个配置项的值
**参数：**
- `key`：配置项键名
- `value`：配置项值
**示例：**
```bash
$ cognix config set report_format table
✅ 配置已更新：report_format = table
```

#### 获取配置项 / config get
```bash
cognix config get <key>
```
**功能：** 获取单个配置项的值
**参数：**
- `key`：配置项键名
**示例：**
```bash
$ cognix config get weekly_report_time
周五 18:00
```

---

### 1.3 规则管理命令

#### 创建周报规则 / rule create-weekly
```bash
cognix rule create-weekly
```
**功能：** 创建每周自动生成周报的规则（创建后需确认才能生效）
**参数：** 无
**示例：**
```bash
$ cognix rule create-weekly
✅ 规则已创建（ID: 1），待确认后生效
📋 规则详情：
  类型：时间触发
  触发时间：每周五 18:00
  动作：生成周报并发送到飞书
  状态：待确认
```

#### 确认规则生效 / rule confirm
```bash
cognix rule confirm <rule_id>
```
**功能：** 确认待审核的规则，使其生效
**参数：**
- `rule_id`：规则 ID
**示例：**
```bash
$ cognix rule confirm 1
✅ 规则 ID 1 已确认生效
```

#### 查看规则列表 / rule list
```bash
cognix rule list [--all]
```
**功能：** 查看所有规则
**参数：**
- `--all`：可选，显示所有规则（包括已禁用和待确认）
**示例：**
```bash
$ cognix rule list
📋 生效规则列表：
ID  | 类型   | 触发条件         | 动作               | 状态  | 触发次数
----|--------|------------------|--------------------|-------|---------
1   | 时间   | 每周五 18:00     | 生成周报           | 生效  | 3
2   | 事件   | 会议前10分钟     | 发送会议提醒       | 生效  | 12
```

#### 删除规则 / rule delete
```bash
cognix rule delete <rule_id>
```
**功能：** 删除指定规则
**参数：**
- `rule_id`：规则 ID
**示例：**
```bash
$ cognix rule delete 1
✅ 规则 ID 1 已删除
```

---

### 1.4 功能命令

#### 生成周报 / weekly-report
```bash
cognix weekly-report [--format <format>] [--send]
```
**功能：** 手动生成上周工作周报
**参数：**
- `--format`：可选，指定输出格式（markdown/table/json），默认使用配置中的格式
- `--send`：可选，生成后自动发送到配置的接收人
**示例：**
```bash
# 生成周报并打印
$ cognix weekly-report
# 生成周报并发送
$ cognix weekly-report --send
✅ 周报已生成并发送给：张三,李四
```

#### 获取建议 / suggest
```bash
cognix suggest <action>
```
**功能：** 触发特定的建议动作
**参数：**
- `action`：动作类型，支持：`generate-weekly`（生成周报）、`meeting-prepare`（会议准备）、`optimize-habit`（习惯优化建议）
**示例：**
```bash
$ cognix suggest generate-weekly
💡 周报生成建议：
  本周你完成了 5 个需求，提交了 12 次代码，参加了 8 个会议
  建议重点突出 XX 项目的进展和遇到的问题
```

---

## 2. Python SDK 接口

### 2.1 配置管理类 / Config

```python
from cognix.utils.config import Config

# 初始化配置
config = Config()

# 方法列表
config.get(key: str, default: Any = None) -> Any
config.set(key: str, value: Any) -> None
config.save() -> None
config.list() -> dict
```

**示例：**
```python
config = Config()
# 获取配置
report_format = config.get("report_format", "markdown")
# 设置配置
config.set("weekly_report_time", "周五 18:00")
config.save()
```

---

### 2.2 偏好存储类 / PreferenceStore

```python
from cognix.core.preference_store import PreferenceStore

# 初始化
store = PreferenceStore()

# 方法列表
store.get_preference(key: str, default: Any = None) -> Any
store.set_preference(key: str, value: Any) -> None
store.delete_preference(key: str) -> None
store.list_preferences() -> dict
```

**示例：**
```python
store = PreferenceStore()
# 保存用户偏好
store.set_preference("meeting_prepare_time", 10)
# 获取偏好
prepare_time = store.get_preference("meeting_prepare_time", 5)
```

---

### 2.3 规则引擎类 / RuleEngine

```python
from cognix.core.rule_engine import RuleEngine

# 初始化
rule_engine = RuleEngine()

# 方法列表
rule_engine.create_rule(rule_data: dict) -> int
rule_engine.confirm_rule(rule_id: int) -> bool
rule_engine.delete_rule(rule_id: int) -> bool
rule_engine.list_rules(include_pending: bool = False) -> list
rule_engine.get_rule(rule_id: int) -> dict | None
```

**示例：**
```python
rule_engine = RuleEngine()
# 创建周报规则
rule_id = rule_engine.create_rule({
    "type": "time",
    "trigger": "0 18 * * 5",
    "action": "generate_weekly_report",
    "name": "每周自动生成周报"
})
# 确认规则生效
rule_engine.confirm_rule(rule_id)
```

---

### 2.4 事件采集类 / EventCollector

```python
from cognix.core.event_collector import EventCollector

# 初始化
collector = EventCollector()

# 方法列表
collector.add_event(event_type: str, content: dict, timestamp: int = None) -> int
collector.query_events(event_type: str = None, start_time: int = None, end_time: int = None, limit: int = 100) -> list
collector.analyze_week_events() -> dict
```

**示例：**
```python
collector = EventCollector()
# 上报事件
collector.add_event("shell_command", {
    "command": "git commit",
    "directory": "/home/user/project",
    "duration": 2.3
})
# 分析上周事件
week_report = collector.analyze_week_events()
```

---

### 2.5 调度器类 / Scheduler

```python
from cognix.core.scheduler import Scheduler

# 初始化
scheduler = Scheduler()

# 方法列表
scheduler.start() -> None
scheduler.stop() -> None
scheduler.add_job(job_func: callable, trigger: str, **trigger_args) -> str
scheduler.remove_job(job_id: str) -> None
scheduler.list_jobs() -> list
scheduler.get_status() -> dict
```

---

### 2.6 飞书 Bot 类 / FeishuBot

```python
from cognix.interfaces.feishu.bot import FeishuBot

# 初始化
bot = FeishuBot(app_id: str, app_secret: str)

# 方法列表
bot.send_message(chat_id: str, content: str, msg_type: str = "text") -> bool
bot.send_card(chat_id: str, card: dict) -> bool
bot.send_weekly_report_card(chat_id: str, report_data: dict) -> bool
bot.send_meeting_reminder_card(chat_id: str, meeting_data: dict) -> bool
```

**示例：**
```python
bot = FeishuBot("cli_xxxxxx", "xxxxxx")
# 发送文本消息
bot.send_message("oc_xxxxxx", "Hello, Cognix!")
# 发送周报卡片
bot.send_weekly_report_card("oc_xxxxxx", {
    "week": "2024年第21周",
    "content": "本周完成5个需求...",
    "receiver": "张三,李四"
})
```

---

## 3. 飞书事件回调接口

如果启用了飞书 Bot，需要在飞书开发者后台配置以下回调地址：

### 事件接收地址
```
POST https://your-domain.com/cognix/feishu/callback
```

### 支持的事件类型
| 事件类型 | 描述 | 处理逻辑 |
|---------|------|---------|
| `im.message.receive_v1` | 接收用户消息 | 响应关键词，处理用户指令 |
| `im.message.reaction.created_v1` | 消息被点赞/回复 | 收集用户反馈，优化记忆 |
| `calendar.event.created_v1` | 日历事件创建 | 自动添加会议提醒规则 |
| `calendar.event.updated_v1` | 日历事件更新 | 更新对应提醒规则 |
| `calendar.event.deleted_v1` | 日历事件删除 | 删除对应提醒规则 |

### 回调请求格式
```json
{
  "schema": "2.0",
  "header": {
    "event_id": "5e3709a478d08573b640e62c76d43d72",
    "token": "xxxxxx",
    "create_time": "1603978800",
    "event_type": "im.message.receive_v1",
    "tenant_key": "xxxxxx",
    "app_id": "cli_xxxxxx"
  },
  "event": {
    "message": {
      "chat_id": "oc_xxxxxx",
      "chat_type": "group",
      "content": "{\"text\":\"@_user_1 生成周报\"}",
      "create_time": "1603978800",
      "message_id": "om_xxxxxx",
      "msg_type": "text"
    },
    "sender": {
      "sender_id": {
        "user_id": "ou_xxxxxx"
      },
      "sender_type": "user"
    }
  }
}
```

---

## 4. 错误码说明

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| 0 | 成功 | - |
| 1001 | 配置文件不存在 | 请先执行 `cognix init` 初始化 |
| 1002 | 配置项不存在 | 检查配置项键名是否正确 |
| 2001 | 规则不存在 | 检查规则 ID 是否正确 |
| 2002 | 规则已存在 | 相同触发条件的规则已创建 |
| 2003 | 规则状态无效 | 待确认的规则无法执行，请先确认 |
| 3001 | 服务未启动 | 请先执行 `cognix start` 启动服务 |
| 3002 | 服务已在运行 | 无需重复启动 |
| 4001 | 飞书配置错误 | 检查飞书 app_id 和 app_secret 是否正确 |
| 4002 | 飞书消息发送失败 | 检查网络连接和飞书权限配置 |
| 5001 | 数据库连接错误 | 检查数据库文件权限或重新初始化 |
| 5002 | 数据写入失败 | 检查磁盘空间和文件权限 |
| 9999 | 未知错误 | 查看日志文件 `~/.cognix/cognix.log` 获取详细信息 |

---

## 5. 数据格式约定

### 时间格式
- 所有时间戳使用毫秒级 Unix 时间戳
- 展示时间默认使用 `YYYY-MM-DD HH:mm:ss` 格式
- 周数使用 ISO 标准周历

### 金额格式
- 所有金额单位为分，使用整数存储，避免浮点数精度问题

### 列表分页
- 分页参数统一使用 `page`（页码，从1开始）和 `page_size`（每页条数，默认20）
- 分页返回格式包含 `total`（总条数）、`page`、`page_size`、`items`（数据列表）