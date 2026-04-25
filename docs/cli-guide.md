# Cognix CLI 使用指南

## 安装

```bash
pip install cognix
```

## 命令总览

```
cognix --help
```

| 命令 | 说明 |
|------|------|
| `cognix remember` | 记录一条记忆 |
| `cognix recall` | 搜索记忆 |
| `cognix context` | 获取近期上下文 |
| `cognix dream` | 手动触发记忆整理 |
| `cognix serve` | 启动后台服务 |

## remember — 记录记忆

将信息保存到记忆系统，支持每日记忆和持久记忆两种模式。

### 基本用法

```bash
cognix remember <heading> <content>
```

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `heading` | string | 是 | 记忆标题，简短概括 |
| `content` | string | 是 | 记忆详细内容 |
| `--persistent` | flag | 否 | 保存到持久记忆（MEMORY.md） |

### 示例

```bash
# 记录每日记忆
cognix remember "会议纪要" "讨论了 Q2 目标，重点在用户增长"

# 记录持久记忆
cognix remember "用户偏好" "用户喜欢用表格格式查看周报" --persistent

# 记录重要决策
cognix remember "技术选型" "决定使用 SQLite + Markdown 双存储方案" --persistent
```

### 输出

```json
{"success": true, "type": "daily"}
```

- `type: "daily"` — 每日记忆
- `type: "persistent"` — 持久记忆

## recall — 搜索记忆

使用 FTS5 全文搜索引擎检索记忆。

### 基本用法

```bash
cognix recall <query>
```

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索关键词 |
| `--limit` | int | 否 | 返回结果数量，默认 10 |
| `--source` | string | 否 | 来源过滤：`memory` 或 `persistent` |

### 示例

```bash
# 搜索所有记忆
cognix recall "周报"

# 限制返回数量
cognix recall "偏好" --limit 5

# 只搜索持久记忆
cognix recall "用户习惯" --source persistent

# 只搜索每日记忆
cognix recall "会议" --source memory
```

### 输出

```json
[
  {
    "id": "uuid-xxx",
    "path": "/home/user/.cognix/memory/2026-04-25.md",
    "source": "memory",
    "start_line": 5,
    "end_line": 12,
    "text": "## 会议纪要\n讨论了 Q2 目标...",
    "score": 1.0
  }
]
```

## context — 获取上下文

获取最近几天的记忆上下文，用于 Agent 对话前的上下文注入。

### 基本用法

```bash
cognix context
```

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--days` | int | 否 | 回溯天数，默认 1 |

### 示例

```bash
# 获取今天的上下文
cognix context

# 获取最近 3 天的上下文
cognix context --days 3

# 获取最近一周的上下文
cognix context --days 7
```

### 输出

返回 Markdown 格式的上下文文本，包含每日记忆和持久记忆。

## dream — 记忆整理

手动触发 Autodream 记忆整理流程，执行去重、冲突解决和偏好提取。

### 基本用法

```bash
cognix dream
```

### 输出

```json
{
  "timestamp": "2026-04-25T21:00:00",
  "deduplication": {
    "found": 3,
    "merged": 3
  },
  "conflict_resolution": {
    "found": 1,
    "pending": 1
  },
  "preference_extraction": {
    "extracted": 5,
    "saved": 5
  }
}
```

### 整理流程

1. **去重**：基于 Jaccard 相似度检测重复记忆（阈值 0.85），自动合并
2. **冲突解决**：检测矛盾偏好（如"喜欢"与"不喜欢"同一事物），标记待确认
3. **偏好提取**：从交互记录中识别用户习惯关键词，保存到偏好存储

## serve — 启动后台服务

启动 Cognix 后台服务，包含 Hook 监听和 Autodream 定时整理。

### 基本用法

```bash
cognix serve
```

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--dream-interval` | int | 否 | Autodream 间隔（小时），默认 24 |

### 示例

```bash
# 默认 24 小时间隔
cognix serve

# 自定义 12 小时间隔
cognix serve --dream-interval 12
```

### 后台服务包含

- **飞书消息 Hook**：监听飞书消息事件，自动记录对话到短期记忆
- **上下文阈值 Hook**：监控短期记忆数量，达到阈值触发压缩
- **Autodream 调度器**：定时执行记忆整理

按 `Ctrl+C` 停止服务。

## Agent 集成方式

Agent 系统通过 shell 调用 CLI 命令与 Cognix 交互：

```python
import subprocess
import json

def remember(heading, content, persistent=False):
    cmd = ["cognix", "remember", heading, content]
    if persistent:
        cmd.append("--persistent")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def recall(query, limit=10):
    cmd = ["cognix", "recall", query, "--limit", str(limit)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def get_context(days=1):
    cmd = ["cognix", "context", "--days", str(days)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

OpenClaw Agent 可直接使用 `skills/cognix-memory.yaml` Skill 描述文件，无需手动编写调用逻辑。
