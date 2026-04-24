import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from cognix.utils.config import config
import hashlib

class FileStore:
    def __init__(self):
        self.base_path = config.events_path
    
    def add_event(self, event_type: str, data: Dict, event_id: Optional[str] = None):
        """添加事件到文件存储"""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = self.base_path / f"{today}.jsonl"
        
        if not event_id:
            event_id = hashlib.md5(f"{datetime.now().isoformat()}{json.dumps(data)}".encode()).hexdigest()[:16]
        
        event = {
            "event_id": event_id,
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        
        return event_id
    
    def get_events(self, 
                  start_date: Optional[str] = None, 
                  end_date: Optional[str] = None, 
                  event_type: Optional[str] = None,
                  limit: Optional[int] = None) -> List[Dict]:
        """查询事件
        :param start_date: 开始日期，格式 YYYY-MM-DD
        :param end_date: 结束日期，格式 YYYY-MM-DD
        :param event_type: 事件类型过滤
        :param limit: 返回结果数量限制
        """
        events = []
        
        for file in sorted(self.base_path.glob("*.jsonl"), reverse=True):
            date_str = file.stem
            
            if start_date and date_str < start_date:
                break
            if end_date and date_str > end_date:
                continue
            
            with open(file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    try:
                        event = json.loads(line.strip())
                        if event_type and event["type"] != event_type:
                            continue
                        events.append(event)
                        if limit and len(events) >= limit:
                            return events
                    except:
                        continue
        
        return events
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """根据事件ID查询事件"""
        for file in self.base_path.glob("*.jsonl"):
            with open(file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if event["event_id"] == event_id:
                            return event
                    except:
                        continue
        return None
    
    def delete_events_before(self, date: str):
        """删除指定日期之前的事件"""
        for file in self.base_path.glob("*.jsonl"):
            date_str = file.stem
            if date_str < date:
                file.unlink()

file_store = FileStore()
