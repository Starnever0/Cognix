from cognix.core.memory_system import get_memory_system


class ConflictResolver:
    """记忆冲突解决 - 检测矛盾记忆，标记待确认"""

    def __init__(self, memory=None):
        self._memory = memory

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_system()
        return self._memory

    def find_conflicts(self) -> list[dict]:
        results = self.memory.search_memory("", limit=1000)
        conflicts = []

        preference_items = []
        for r in results:
            text = r.get("text", "").lower()
            if any(kw in text for kw in ["偏好", "喜欢", "习惯", "prefer", "like"]):
                preference_items.append(r)

        for i, item_a in enumerate(preference_items):
            for j in range(i + 1, len(preference_items)):
                item_b = preference_items[j]
                if self._is_conflict(item_a["text"], item_b["text"]):
                    conflicts.append({
                        "items": [item_a, item_b],
                        "reason": "潜在偏好冲突",
                    })

        return conflicts

    def resolve_conflict(self, conflict: dict, keep_id: str) -> dict:
        items = conflict["items"]
        kept = None
        removed = []

        for item in items:
            if item["id"] == keep_id:
                kept = item
            else:
                removed.append(item)

        return {
            "kept": kept,
            "removed": removed,
            "resolved": kept is not None,
        }

    def _is_conflict(self, text_a: str, text_b: str) -> bool:
        negation_words = ["不喜欢", "不要", "不用", "讨厌", "don't", "not", "never"]
        has_negation_a = any(w in text_a.lower() for w in negation_words)
        has_negation_b = any(w in text_b.lower() for w in negation_words)

        if has_negation_a != has_negation_b:
            set_a = set(text_a.lower().split())
            set_b = set(text_b.lower().split())
            overlap = set_a & set_b
            content_words = set_a | set_b
            negation_set = set(w.lower() for w in negation_words)
            content_words -= negation_set

            if content_words and len(overlap - negation_set) / len(content_words) > 0.3:
                return True

        return False
