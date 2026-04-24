from typing import Dict, List, Optional
from cognix.storage.sqlite_store import sqlite_store
from cognix.core.preference_store import preference_store

class RuleEngine:
    def __init__(self):
        self.store = sqlite_store
    
    def create_rule(self, name: str, trigger: str, action: Dict, status: str = "pending") -> int:
        """创建新规则，默认待确认状态"""
        return self.store.add_rule(name, trigger, action, status)
    
    def confirm_rule(self, rule_id: int) -> bool:
        """确认规则，激活生效"""
        rule = self.store.get_rule(rule_id)
        if rule and rule["status"] == "pending":
            self.store.update_rule_status(rule_id, "active")
            return True
        return False
    
    def reject_rule(self, rule_id: int) -> bool:
        """拒绝规则，禁用"""
        rule = self.store.get_rule(rule_id)
        if rule and rule["status"] == "pending":
            self.store.update_rule_status(rule_id, "disabled")
            return True
        return False
    
    def disable_rule(self, rule_id: int) -> bool:
        """禁用已激活的规则"""
        rule = self.store.get_rule(rule_id)
        if rule and rule["status"] == "active":
            self.store.update_rule_status(rule_id, "disabled")
            return True
        return False
    
    def enable_rule(self, rule_id: int) -> bool:
        """启用已禁用的规则"""
        rule = self.store.get_rule(rule_id)
        if rule and rule["status"] == "disabled":
            self.store.update_rule_status(rule_id, "active")
            return True
        return False
    
    def get_active_rules(self) -> List[Dict]:
        """获取所有激活的规则"""
        return self.store.list_rules(status="active")
    
    def get_pending_rules(self) -> List[Dict]:
        """获取待确认的规则"""
        return self.store.list_rules(status="pending")
    
    def get_all_rules(self) -> List[Dict]:
        """获取所有规则"""
        return self.store.list_rules()
    
    def get_rule(self, rule_id: int) -> Optional[Dict]:
        """获取指定规则"""
        return self.store.get_rule(rule_id)
    
    def update_rule_action(self, rule_id: int, action: Dict) -> bool:
        """更新规则动作"""
        rule = self.store.get_rule(rule_id)
        if rule:
            self.store.update_rule(rule_id, action=action)
            return True
        return False
    
    def generate_weekly_report_rule(self, time: str = "15:55", day_of_week: str = "fri") -> int:
        """生成周报规则
        :param time: 触发时间，格式 HH:MM
        :param day_of_week: 触发星期，mon/tue/wed/thu/fri/sat/sun
        """
        hour, minute = time.split(":")
        action = {
            "type": "weekly_report",
            "format": preference_store.get_report_format(),
            "receiver": preference_store.get_weekly_report_receiver(),
            "template": "default"
        }
        trigger = f"cron: {minute} {hour} * * {day_of_week}"
        return self.create_rule("每周周报提醒", trigger, action)
    
    def generate_meeting_reminder_rule(self, meeting_time: str, day_of_week: str, before_minutes: int = 5) -> int:
        """生成会议提醒规则
        :param meeting_time: 会议时间，格式 HH:MM
        :param day_of_week: 会议星期
        :param before_minutes: 提前提醒分钟数
        """
        hour, minute = map(int, meeting_time.split(":"))
        total_minutes = hour * 60 + minute - before_minutes
        trigger_hour = total_minutes // 60
        trigger_minute = total_minutes % 60
        
        action = {
            "type": "meeting_reminder",
            "meeting_time": meeting_time,
            "before_minutes": before_minutes,
            "content": "已整理上周待办事项"
        }
        trigger = f"cron: {trigger_minute} {trigger_hour} * * {day_of_week}"
        return self.create_rule("会议提醒", trigger, action)

rule_engine = RuleEngine()
