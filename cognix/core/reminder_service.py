import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta

@dataclass
class Reminder:
    """
    提醒数据类
    """
    id: str
    name: str
    trigger: str  # 触发条件：friday_17_00, daily_09_00, monthly_1_09_00, once
    description: str
    action: str  # 触发后执行的动作
    params: Dict = None
    enabled: bool = True
    last_triggered: Optional[str] = None
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger,
            "description": self.description,
            "action": self.action,
            "params": self.params,
            "enabled": self.enabled,
            "last_triggered": self.last_triggered,
            "created_at": self.created_at
        }

class ReminderService:
    """
    主动提醒服务
    负责管理定时提醒、周期性任务提醒，支持飞书卡片交互
    
    典型提醒场景：
    - 周五 17:00 周报提醒
    - 会议前 5 分钟材料提醒
    - 月底报销提醒
    - 待办事项逾期提醒
    """
    
    def __init__(self, reminders_dir: Optional[str] = None):
        if reminders_dir:
            self.reminders_dir = Path(reminders_dir)
        else:
            from cognix.utils.config import config
            self.reminders_dir = config.home_path / "reminders"
        
        self.reminders_dir.mkdir(parents=True, exist_ok=True)
        
        # 触发器映射
        self.trigger_patterns = {
            # 每周
            "monday_09_00": "0 9 * * 0",
            "tuesday_09_00": "0 9 * * 1",
            "wednesday_09_00": "0 9 * * 2",
            "thursday_09_00": "0 9 * * 3",
            "friday_09_00": "0 9 * * 4",
            "friday_17_00": "0 17 * * 4",
            "saturday_09_00": "0 9 * * 5",
            "sunday_09_00": "0 9 * * 6",
            
            # 每天
            "daily_09_00": "0 9 * * *",
            "daily_12_00": "0 12 * * *",
            "daily_18_00": "0 18 * * *",
            "daily_20_00": "0 20 * * *",
            
            # 每月
            "monthly_1_09_00": "0 9 1 * *",
            "monthly_15_09_00": "0 9 15 * *",
            "monthly_last_18_00": "0 18 L * *",
        }
    
    def _generate_id(self, name: str) -> str:
        """生成唯一ID"""
        return f"{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
    
    def add_reminder(self, name: str, trigger: str, description: str, 
                     action: str, params: Optional[Dict] = None) -> Dict:
        """
        添加提醒
        :param name: 提醒名称
        :param trigger: 触发条件
        :param description: 提醒描述
        :param action: 触发后执行的动作
        :param params: 动作参数
        :return: 提醒字典
        """
        reminder = Reminder(
            id=self._generate_id(name),
            name=name,
            trigger=trigger,
            description=description,
            action=action,
            params=params
        )
        
        file_path = self.reminders_dir / f"{reminder.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(reminder.to_dict(), f, ensure_ascii=False, indent=2)
        
        return reminder.to_dict()
    
    def get_reminder(self, reminder_id: str) -> Optional[Dict]:
        """
        获取提醒
        :param reminder_id: 提醒ID
        :return: 提醒字典，如果不存在返回None
        """
        file_path = self.reminders_dir / f"{reminder_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_reminder_by_name(self, name: str) -> Optional[Dict]:
        """
        根据名称获取提醒
        :param name: 提醒名称
        :return: 提醒字典，如果不存在返回None
        """
        for json_file in self.reminders_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    reminder = json.load(f)
                    if reminder.get("name") == name:
                        return reminder
            except Exception:
                pass
        return None
    
    def list_reminders(self) -> List[Dict]:
        """
        获取所有提醒列表
        :return: 提醒列表
        """
        reminders = []
        for json_file in self.reminders_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    reminder = json.load(f)
                    reminders.append(reminder)
            except Exception:
                pass
        
        return sorted(reminders, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def update_reminder(self, reminder_id: str, **kwargs) -> Optional[Dict]:
        """
        更新提醒
        :param reminder_id: 提醒ID
        :param kwargs: 要更新的字段
        :return: 更新后的提醒字典，如果不存在返回None
        """
        reminder = self.get_reminder(reminder_id)
        if not reminder:
            return None
        
        reminder.update(kwargs)
        
        file_path = self.reminders_dir / f"{reminder_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(reminder, f, ensure_ascii=False, indent=2)
        
        return reminder
    
    def remove_reminder(self, name_or_id: str) -> bool:
        """
        删除提醒
        :param name_or_id: 提醒名称或ID
        :return: 是否删除成功
        """
        # 先尝试按ID删除
        file_path = self.reminders_dir / f"{name_or_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        
        # 再尝试按名称查找并删除
        reminder = self.get_reminder_by_name(name_or_id)
        if reminder:
            file_path = self.reminders_dir / f"{reminder['id']}.json"
            if file_path.exists():
                file_path.unlink()
                return True
        
        return False
    
    def _parse_trigger(self, trigger: str) -> str:
        """
        解析触发器为Cron表达式
        :param trigger: 触发器字符串
        :return: Cron表达式
        """
        # 检查预定义模式
        if trigger in self.trigger_patterns:
            return self.trigger_patterns[trigger]
        
        # 尝试解析自定义模式
        # 支持的格式：daily_HH_MM, weekly_DAY_HH_MM, monthly_DAY_HH_MM
        parts = trigger.split('_')
        
        if len(parts) >= 3:
            frequency = parts[0]
            hour = parts[-2]
            minute = parts[-1]
            
            if frequency == "daily":
                return f"{minute} {hour} * * *"
            elif frequency == "weekly" and len(parts) == 4:
                day_name = parts[1].lower()
                day_map = {
                    "monday": "0", "tuesday": "1", "wednesday": "2",
                    "thursday": "3", "friday": "4", "saturday": "5", "sunday": "6"
                }
                day = day_map.get(day_name, "*")
                return f"{minute} {hour} * * {day}"
            elif frequency == "monthly" and len(parts) == 4:
                day = parts[1]
                return f"{minute} {hour} {day} * *"
        
        # 默认返回空，表示一次性触发
        return ""
    
    def check_due_reminders(self) -> List[Dict]:
        """
        检查到期的提醒
        :return: 到期提醒列表
        """
        due_reminders = []
        now = datetime.now()
        
        for reminder in self.list_reminders():
            if not reminder.get("enabled", True):
                continue
            
            trigger = reminder.get("trigger", "")
            
            # 一次性触发的提醒
            if trigger == "once":
                due_reminders.append(reminder)
                continue
            
            # 简单的时间匹配检查
            parts = trigger.split('_')
            if len(parts) >= 3:
                try:
                    hour = int(parts[-2])
                    minute = int(parts[-1])
                    
                    # 检查是否是今天的这个时间
                    if now.hour == hour and now.minute == minute:
                        # 检查是否是正确的日期（对于每周/每月）
                        if len(parts) == 4:
                            if parts[0] == "weekly":
                                day_name = parts[1].lower()
                                day_map = {
                                    "monday": 0, "tuesday": 1, "wednesday": 2,
                                    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
                                }
                                if now.weekday() == day_map.get(day_name, -1):
                                    due_reminders.append(reminder)
                            elif parts[0] == "monthly":
                                day = int(parts[1])
                                if now.day == day:
                                    due_reminders.append(reminder)
                        else:
                            # daily
                            due_reminders.append(reminder)
                except ValueError:
                    pass
        
        return due_reminders
    
    def trigger_reminder(self, reminder_id: str, 
                        action_handler: Optional[Callable] = None) -> Dict:
        """
        触发提醒
        :param reminder_id: 提醒ID
        :param action_handler: 动作处理函数
        :return: 触发结果
        """
        reminder = self.get_reminder(reminder_id)
        if not reminder:
            return {"success": False, "error": "提醒不存在"}
        
        if not reminder.get("enabled", True):
            return {"success": False, "error": "提醒已禁用"}
        
        # 更新最后触发时间
        self.update_reminder(reminder_id, last_triggered=datetime.now().isoformat())
        
        # 执行动作
        action = reminder.get("action")
        params = reminder.get("params", {})
        
        if action_handler:
            try:
                result = action_handler(action, params)
                return {"success": True, "reminder": reminder, "result": result}
            except Exception as e:
                return {"success": False, "reminder": reminder, "error": str(e)}
        
        return {"success": True, "reminder": reminder, "action": action, "params": params}


# 全局实例
_reminder_service_instance: Optional[ReminderService] = None

def get_reminder_service() -> ReminderService:
    """获取全局提醒服务实例"""
    global _reminder_service_instance
    if _reminder_service_instance is None:
        _reminder_service_instance = ReminderService()
    return _reminder_service_instance
