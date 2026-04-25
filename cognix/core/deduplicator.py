from cognix.core.memory_system import get_memory_system


class MemoryDeduplicator:
    """记忆去重 - 基于内容相似度检测重复记忆"""

    SIMILARITY_THRESHOLD = 0.85

    def __init__(self, memory=None):
        self._memory = memory

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_system()
        return self._memory

    def find_duplicates(self, source: str = None) -> list[dict]:
        results = self.memory.search_memory("", limit=1000, source=source)
        if len(results) < 2:
            return []

        duplicates = []
        seen = set()

        for i, item_a in enumerate(results):
            if item_a["id"] in seen:
                continue
            for j in range(i + 1, len(results)):
                item_b = results[j]
                if item_b["id"] in seen:
                    continue

                similarity = self._compute_similarity(item_a["text"], item_b["text"])
                if similarity >= self.SIMILARITY_THRESHOLD:
                    duplicates.append({
                        "items": [item_a, item_b],
                        "similarity": similarity,
                    })
                    seen.add(item_b["id"])

        return duplicates

    def merge_duplicates(self, duplicate_ids: list[str], keep_first: bool = True) -> str:
        if not duplicate_ids:
            return ""

        results = self.memory.search_memory("", limit=1000)
        id_map = {r["id"]: r for r in results}

        kept_id = duplicate_ids[0] if keep_first else duplicate_ids[-1]
        removed = []

        for did in duplicate_ids[1:] if keep_first else duplicate_ids[:-1]:
            removed.append(did)

        return kept_id

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        if text_a == text_b:
            return 1.0

        set_a = set(text_a.lower().split())
        set_b = set(text_b.lower().split())

        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0

        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)
