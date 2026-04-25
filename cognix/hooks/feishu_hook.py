from cognix.hooks.base import BaseHook
from cognix.core.memory_system import get_memory_system
from cognix.utils.config import config


class FeishuHook(BaseHook):
    """飞书消息Hook - 监听飞书消息事件，自动记录对话到短期记忆"""

    def __init__(self):
        self._memory = None
        self._running = False

    @property
    def name(self) -> str:
        return "feishu"

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_system()
        return self._memory

    def on_event(self, event_type: str, data: dict) -> None:
        if event_type != "feishu_message":
            return

        user_open_id = data.get("user_open_id", "unknown")
        content = data.get("content", "")
        message_id = data.get("message_id", "")

        if not content:
            return

        session_id = f"feishu_{user_open_id}"
        self.memory.add_short_term(session_id, "message", {
            "content": content,
            "message_id": message_id,
            "direction": data.get("direction", "inbound"),
        })

    def start(self) -> None:
        if config.feishu_app_id and config.feishu_app_secret:
            self._running = True

    def stop(self) -> None:
        self._running = False
