import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class EventStore:
    """事件存储（内存模式，回退到文件）"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            from cognix.utils.config import config
            storage_dir = getattr(config, 'storage_dir', './data/events')
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._events_file = self.storage_dir / "events.json"
        self._load_events()

    def _load_events(self):
        if self._events_file.exists():
            try:
                with open(self._events_file, 'r', encoding='utf-8') as f:
                    self._events = json.load(f)
            except:
                self._events = []
        else:
            self._events = []

    def _save_events(self):
        with open(self._events_file, 'w', encoding='utf-8') as f:
            json.dump(self._events[-1000:], f, ensure_ascii=False, indent=2)

    def add_event(self, event_type: str, event_data: Dict[str, Any]) -> str:
        event_id = str(uuid.uuid4())[:8]
        event = {
            "event_id": event_id,
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.now().isoformat()
        }
        self._events.append(event)
        self._save_events()
        return event_id

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._events[-limit:]

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        for event in reversed(self._events):
            if event["event_id"] == event_id:
                return event
        return None


file_store = EventStore()