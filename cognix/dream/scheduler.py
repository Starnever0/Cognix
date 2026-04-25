import threading
from datetime import datetime
from cognix.core.deduplicator import MemoryDeduplicator
from cognix.core.conflict_resolver import ConflictResolver
from cognix.core.preference_extractor import PreferenceExtractor


class AutodreamScheduler:
    """Autodream定时整理调度器 - 协调去重/冲突解决/偏好提取"""

    def __init__(self):
        self._deduplicator = MemoryDeduplicator()
        self._conflict_resolver = ConflictResolver()
        self._preference_extractor = PreferenceExtractor()
        self._timer = None
        self._running = False

    def run_once(self) -> dict:
        report = {
            "timestamp": datetime.now().isoformat(),
            "deduplication": self._run_deduplication(),
            "conflict_resolution": self._run_conflict_resolution(),
            "preference_extraction": self._run_preference_extraction(),
        }
        return report

    def start(self, interval_hours: int = 24):
        self._running = True
        self._schedule_next(interval_hours)

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self, interval_hours: int):
        if not self._running:
            return
        self._timer = threading.Timer(interval_hours * 3600, self._run_scheduled, args=[interval_hours])
        self._timer.daemon = True
        self._timer.start()

    def _run_scheduled(self, interval_hours: int):
        try:
            self.run_once()
        except Exception:
            pass
        self._schedule_next(interval_hours)

    def _run_deduplication(self) -> dict:
        duplicates = self._deduplicator.find_duplicates()
        merged = 0
        for dup in duplicates:
            ids = [item["id"] for item in dup["items"]]
            self._deduplicator.merge_duplicates(ids)
            merged += 1
        return {"found": len(duplicates), "merged": merged}

    def _run_conflict_resolution(self) -> dict:
        conflicts = self._conflict_resolver.find_conflicts()
        return {"found": len(conflicts), "pending": len(conflicts)}

    def _run_preference_extraction(self) -> dict:
        preferences = self._preference_extractor.extract_from_interactions()
        saved = self._preference_extractor.save_preferences(preferences)
        return {"extracted": len(preferences), "saved": saved}
