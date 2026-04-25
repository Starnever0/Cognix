import json
from typing import Optional
from cognix.interfaces.feishu.client import FeishuClient
from cognix.hooks import HookRegistry


class FeishuEventHandler:
    """飞书事件路由与处理 - 接收飞书回调，分发到Hook系统"""

    def __init__(self):
        self._client = FeishuClient()
        self._hook_registry: Optional[HookRegistry] = None

    @property
    def hook_registry(self):
        if self._hook_registry is None:
            from cognix.hooks import HookRegistry
            self._hook_registry = HookRegistry()
        return self._hook_registry

    def handle_event(self, event: dict) -> dict:
        header = event.get("header", {})
        event_type = header.get("event_type")
        event_data = event.get("event", {})

        if not event_type:
            return {"code": 0}

        if event_type == "im.message.receive_v1":
            return self._handle_message_receive(event_data)

        return {"code": 0}

    def _handle_message_receive(self, event_data: dict) -> dict:
        message = event_data.get("message", {})
        sender = event_data.get("sender", {})

        content = ""
        try:
            raw = json.loads(message.get("content", "{}"))
            content = raw.get("text", "")
        except (json.JSONDecodeError, AttributeError):
            pass

        user_open_id = sender.get("sender_id", {}).get("open_id", "")

        self.hook_registry.dispatch("feishu_message", {
            "user_open_id": user_open_id,
            "content": content,
            "message_id": message.get("message_id", ""),
            "direction": "inbound",
        })

        return {"code": 0}
