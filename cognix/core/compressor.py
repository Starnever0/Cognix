from cognix.core.memory_system import get_memory_system


class MemoryCompressor:
    """短期记忆压缩策略 - 提取关键信息，生成摘要，转为长期记忆"""

    def __init__(self, memory=None):
        self._memory = memory

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_system()
        return self._memory

    def should_compress(self, session_id: str) -> bool:
        items = self.memory.get_short_term(session_id)
        return len(items) >= 20

    def compress(self, session_id: str) -> dict:
        items = self.memory.get_short_term(session_id)
        if not items:
            return {"compressed": 0, "heading": "", "summary": ""}

        messages = []
        for item in items:
            value = item.get("value", {})
            if isinstance(value, dict) and "content" in value:
                messages.append(value["content"])
            elif isinstance(value, str):
                messages.append(value)

        summary = self._generate_summary(messages)
        heading = self._generate_heading(session_id, messages)

        self.memory.add_memory(heading, summary)

        self.memory.clear_short_term(session_id)

        return {
            "compressed": len(items),
            "heading": heading,
            "summary": summary,
        }

    def _generate_summary(self, messages: list[str]) -> str:
        if not messages:
            return ""

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        if len(messages) <= 3:
            body = "\n".join(f"- {m}" for m in messages)
        else:
            body = "\n".join(f"- {m}" for m in messages[:5])
            body += f"\n- ... 以及其他 {len(messages) - 5} 条消息"

        return f"压缩时间: {timestamp}\n原始消息数: {len(messages)}\n\n{body}"

    def _generate_heading(self, session_id: str, messages: list[str]) -> str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"会话摘要 [{session_id}] {date_str}"
