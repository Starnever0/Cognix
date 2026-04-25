# Cognix 飞书集成指南

## 概述

Cognix 通过飞书 Hook 监听消息事件，自动将对话内容记录到记忆系统。同时提供飞书 API 客户端，支持向用户发送消息。

## 架构

```
飞书服务器 → 事件回调 → FeishuEventHandler → HookRegistry → FeishuHook → 短期记忆
                                                              │
                                                        达到阈值触发压缩
                                                              │
                                                              ▼
                                              每日记忆(Markdown) + 持久记忆
```

## 前置条件

1. 在[飞书开放平台](https://open.feishu.cn/)创建应用
2. 获取 App ID 和 App Secret
3. 开启机器人能力
4. 订阅 `im.message.receive_v1` 事件

## 配置

在 `~/.cognix/.env` 中配置飞书凭证：

```env
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=xxxxxx
```

未配置时，飞书 Hook 不会启动，不影响其他功能。

## 模块说明

### FeishuClient — 飞书 API 客户端

封装飞书 API 调用，提供消息发送和事件验证能力。

```python
from cognix.interfaces.feishu.client import FeishuClient

client = FeishuClient()

# 检查是否可用
client.is_available()

# 发送文本消息
client.send_text_message("open_id", "ou_xxxxxx", "你好")
```

### FeishuEventHandler — 事件处理器

接收飞书回调事件，路由到 Hook 系统。

```python
from cognix.interfaces.feishu.event_handler import FeishuEventHandler

handler = FeishuEventHandler()

# 处理飞书事件回调
result = handler.handle_event({
    "header": {"event_type": "im.message.receive_v1"},
    "event": {
        "message": {
            "content": '{"text": "你好"}',
            "message_id": "om_xxxxxx"
        },
        "sender": {
            "sender_id": {"open_id": "ou_xxxxxx"}
        }
    }
})
```

### FeishuHook — 飞书消息 Hook

监听 `feishu_message` 事件，自动将对话内容记录到短期记忆。

```python
from cognix.hooks.feishu_hook import FeishuHook

hook = FeishuHook()

# 处理飞书消息事件
hook.on_event("feishu_message", {
    "user_open_id": "ou_xxxxxx",
    "content": "帮我生成周报",
    "message_id": "om_xxxxxx",
    "direction": "inbound",
})
```

消息会以 `feishu_<open_id>` 作为 session_id 存入短期记忆。

## 数据流

1. 飞书服务器推送 `im.message.receive_v1` 事件
2. `FeishuEventHandler` 解析消息内容和发送者信息
3. 通过 `HookRegistry` 分发 `feishu_message` 事件
4. `FeishuHook` 将消息记录到短期记忆（session_id = `feishu_<open_id>`）
5. 当短期记忆达到阈值，`ContextThresholdHook` 触发压缩
6. 压缩结果写入每日记忆和持久记忆

## OpenClaw Agent 集成

### 方式一：Skill 描述文件

将 `skills/cognix-memory.yaml` 添加到 OpenClaw Agent 的 Skill 目录。Agent 会自动识别 `remember`、`recall`、`context`、`dream` 四个工具。

### 方式二：直接调用 CLI

Agent 在对话中通过 shell 调用 Cognix CLI：

```bash
# 记住用户偏好
cognix remember "用户偏好" "用户喜欢简洁的回复风格"

# 回忆之前的讨论
cognix recall "上周讨论的方案"

# 获取近期上下文
cognix context --days 3
```

## Webhook 服务部署

如果需要接收飞书事件回调，需要部署一个 Webhook 服务。以下是一个基于 Flask 的示例：

```python
from flask import Flask, request
from cognix.interfaces.feishu.event_handler import FeishuEventHandler

app = Flask(__name__)
handler = FeishuEventHandler()

@app.route("/feishu/webhook", methods=["POST"])
def feishu_webhook():
    event = request.json
    result = handler.handle_event(event)
    return result

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

同时在飞书开放平台配置请求地址为 `http://your-server:8080/feishu/webhook`。

## 注意事项

- 飞书 Hook 仅在配置了 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 后启动
- 短期记忆存储在内存中，服务重启后会丢失
- 建议配合 `cognix serve` 使用，确保 Autodream 定期整理记忆
- 发送消息需要应用具有 `im:message:send_as_bot` 权限
