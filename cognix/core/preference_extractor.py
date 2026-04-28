from cognix.core.memory_system import get_memory_system
from cognix.core.preference_store import PreferenceStore
from cognix.storage.sqlite_store import sqlite_store


class PreferenceExtractor:
    """偏好提取 - 从交互记录中识别用户习惯并保存"""

    PREFERENCE_PATTERNS = {
        "report_format": ["表格", "table", "markdown", "md格式"],
        "output_language": ["中文", "英文", "english", "chinese"],
        "meeting_reminder": ["提前", "提醒", "分钟前"],
        "dnd_time_range": ["免打扰", "勿扰", "休息时间", "dnd"],
    }

    def __init__(self, memory=None, preference_store=None):
        self._memory = memory
        self._preference_store = preference_store

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_system()
        return self._memory

    @property
    def preference_store(self):
        if self._preference_store is None:
            self._preference_store = PreferenceStore()
        return self._preference_store

    def extract_from_interactions(self, days: int = 7) -> list[dict]:
        results = self.memory.search_memory("", limit=200)
        preferences = []

        for item in results:
            text = item.get("text", "").lower()
            extracted = self._extract_preferences(text)
            for key, value in extracted.items():
                preferences.append({
                    "key": key,
                    "value": value,
                    "source_id": item["id"],
                    "source_text": item["text"][:100],
                })

        return preferences

    def save_preferences(self, preferences: list[dict]) -> int:
        saved = 0
        for pref in preferences:
            key = pref["key"]
            value = pref["value"]
            self.preference_store.set(key, {"value": value})
            saved += 1
        return saved

    def _extract_preferences(self, text: str) -> dict:
        found = {}

        for key, patterns in self.PREFERENCE_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    value = self._infer_preference_value(key, pattern, text)
                    if value:
                        found[key] = value
                    break

        return found

    def _infer_preference_value(self, key: str, pattern: str, text: str) -> str:
        if key == "report_format":
            if "表格" in text or "table" in text:
                return "table"
            if "markdown" in text or "md格式" in text:
                return "markdown"

        elif key == "output_language":
            if "中文" in text:
                return "zh-CN"
            if "英文" in text or "english" in text:
                return "en"

        elif key == "meeting_reminder":
            import re
            match = re.search(r"(\d+)\s*分钟前", text)
            if match:
                return str(match.group(1))

        elif key == "dnd_time_range":
            import re
            match = re.search(r"(\d{1,2}:\d{2})\s*[-到至]\s*(\d{1,2}:\d{2})", text)
            if match:
                return f"{match.group(1)}-{match.group(2)}"

        return ""
