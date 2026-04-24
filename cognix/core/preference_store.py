from typing import Dict, Optional, List
from cognix.storage.sqlite_store import sqlite_store

class PreferenceStore:
    def __init__(self):
        self.store = sqlite_store
    
    def set(self, key: str, value: Dict, weight: float = 1.0):
        """设置用户偏好
        :param key: 偏好键名
        :param value: 偏好值，字典格式
        :param weight: 偏好权重，0-1，越高优先级越高
        """
        old_value = self.get(key)
        if old_value:
            # 偏好更新时权重增加
            weight = min(weight + 0.1, 1.0)
        self.store.set_preference(key, value, weight)
        return old_value
    
    def get(self, key: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """获取用户偏好"""
        value = self.store.get_preference(key)
        return value if value is not None else default
    
    def list(self) -> List[Dict]:
        """列出所有偏好"""
        return self.store.list_preferences()
    
    def delete(self, key: str) -> bool:
        """删除指定偏好"""
        exists = self.get(key) is not None
        if exists:
            self.store.delete_preference(key)
        return exists
    
    # 常用快捷方法
    def get_report_format(self) -> str:
        """获取报告输出格式，默认 table"""
        pref = self.get("report_format")
        return pref.get("value", "table") if pref else "table"
    
    def get_weekly_report_receiver(self) -> str:
        """获取周报接收人"""
        pref = self.get("weekly_report_receiver")
        return pref.get("value", "") if pref else ""
    
    def get_meeting_reminder_time(self) -> int:
        """获取会议提醒提前时间（分钟），默认 5 分钟"""
        pref = self.get("meeting_reminder")
        return pref.get("value", 5) if pref else 5
    
    def get_output_language(self) -> str:
        """获取输出语言，默认中文"""
        pref = self.get("output_language")
        return pref.get("value", "zh-CN") if pref else "zh-CN"
    
    def get_dnd_time_range(self) -> tuple:
        """获取免打扰时间段，默认 (22:00, 08:00)"""
        pref = self.get("dnd_time_range")
        return pref.get("value", ("22:00", "08:00")) if pref else ("22:00", "08:00")

preference_store = PreferenceStore()
