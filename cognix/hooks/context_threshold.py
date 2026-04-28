from cognix.hooks.base import BaseHook
from cognix.core.memory_system import get_memory_system


class ContextThresholdHook(BaseHook):
    """上下文阈值Hook - 监控短期记忆数量，达到阈值时触发压缩"""

    DEFAULT_THRESHOLD = 50

    def __init__(self, threshold: int = None):
        self._threshold = threshold or self.DEFAULT_THRESHOLD
        self._memory = None
        self._running = False

    @property
    def name(self) -> str:
        return "context_threshold"

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_system()
        return self._memory

    def on_event(self, event_type: str, data: dict) -> None:
        if event_type != "short_term_add":
            return

        session_id = data.get("session_id", "")
        if not session_id:
            return

        items = self.memory.get_short_term(session_id)
        if len(items) >= self._threshold:
            from cognix.core.compressor import MemoryCompressor
            compressor = MemoryCompressor()
            compressor.compress(session_id)

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
