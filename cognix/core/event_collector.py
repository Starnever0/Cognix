from typing import Dict, Optional
from cognix.storage.file_store import file_store
from cognix.core.preference_store import preference_store
from cognix.core.rule_engine import rule_engine

class EventCollector:
    def __init__(self):
        self.store = file_store
    
    def track_cli_command(self, command: str, args: Optional[Dict] = None, exit_code: int = 0) -> str:
        """跟踪 CLI 命令执行
        :param command: 命令名称
        :param args: 命令参数
        :param exit_code: 执行退出码
        """
        event_data = {
            "command": command,
            "args": args or {},
            "exit_code": exit_code
        }
        event_id = self.store.add_event("cli_command", event_data)
        
        # 高频命令自动学习
        self._learn_from_cli_command(command, args)
        
        return event_id
    
    def track_feishu_interaction(self, event_type: str, user_open_id: str, data: Dict) -> str:
        """跟踪飞书交互事件
        :param event_type: 事件类型：message_receive/action_click/card_callback
        :param user_open_id: 用户飞书 OpenID
        :param data: 事件数据
        """
        event_data = {
            "event_type": event_type,
            "user_open_id": user_open_id,
            **data
        }
        event_id = self.store.add_event("feishu_interaction", event_data)
        
        # 飞书交互学习
        self._learn_from_feishu_event(event_type, data)
        
        return event_id
    
    def track_user_feedback(self, rule_id: int, action: str, feedback: str = "") -> str:
        """跟踪用户反馈
        :param rule_id: 规则ID
        :param action: 反馈动作：confirm/reject/modify
        :param feedback: 反馈内容
        """
        event_data = {
            "rule_id": rule_id,
            "action": action,
            "feedback": feedback
        }
        event_id = self.store.add_event("user_feedback", event_data)
        
        # 根据用户反馈调整规则和偏好
        self._learn_from_feedback(rule_id, action, feedback)
        
        return event_id
    
    def track_preference_change(self, key: str, old_value: Optional[Dict], new_value: Dict) -> str:
        """跟踪偏好变更
        :param key: 偏好键
        :param old_value: 旧值
        :param new_value: 新值
        """
        event_data = {
            "key": key,
            "old_value": old_value,
            "new_value": new_value
        }
        return self.store.add_event("preference_change", event_data)
    
    def track_calendar_event(self, event_type: str, event_data: Dict) -> str:
        """跟踪日历事件
        :param event_type: 事件类型：meeting_created/meeting_updated/meeting_reminder
        :param event_data: 日历事件详情
        """
        return self.store.add_event("calendar_event", {"event_type": event_type, **event_data})
    
    def _learn_from_cli_command(self, command: str, args: Optional[Dict]):
        """从 CLI 命令中学习规律"""
        # 周报命令学习
        if command == "weekly-report" or "weekly" in str(args):
            # 如果用户多次手动生成周报，自动生成规则建议
            recent_events = self.store.get_events(event_type="cli_command", limit=10)
            weekly_count = sum(1 for e in recent_events if "weekly" in str(e["data"].get("command", "")) or "weekly" in str(e["data"].get("args", "")))
            if weekly_count >= 3:
                # 自动建议创建周报规则
                existing_rules = rule_engine.get_all_rules()
                has_weekly_rule = any("周报" in r["name"] for r in existing_rules)
                if not has_weekly_rule:
                    rule_engine.create_rule(
                        name="建议：每周周报提醒",
                        trigger="cron: 55 15 * * fri",
                        action={
                            "type": "weekly_report",
                            "format": preference_store.get_report_format(),
                            "receiver": preference_store.get_weekly_report_receiver()
                        },
                        status="pending"
                    )
    
    def _learn_from_feishu_event(self, event_type: str, data: Dict):
        """从飞书事件中学习规律"""
        if event_type == "message_receive":
            content = data.get("content", "")
            if "周报" in content and ("生成" in content or "写" in content):
                # 用户多次请求周报时自动建议规则
                recent_events = self.store.get_events(event_type="feishu_interaction", limit=5)
                weekly_count = sum(1 for e in recent_events if "周报" in str(e["data"].get("content", "")))
                if weekly_count >= 3:
                    existing_rules = rule_engine.get_all_rules()
                    has_weekly_rule = any("周报" in r["name"] for r in existing_rules)
                    if not has_weekly_rule:
                        rule_engine.generate_weekly_report_rule()
    
    def _learn_from_feedback(self, rule_id: int, action: str, feedback: str):
        """根据用户反馈优化规则和偏好"""
        if action == "confirm":
            # 用户确认规则，增加相关偏好权重
            rule = rule_engine.get_rule(rule_id)
            if rule and rule["action"]["type"] == "weekly_report":
                if rule["action"].get("format"):
                    preference_store.set("report_format", {"value": rule["action"]["format"]}, weight=1.0)
                if rule["action"].get("receiver"):
                    preference_store.set("weekly_report_receiver", {"value": rule["action"]["receiver"]}, weight=1.0)
        elif action == "reject":
            # 用户拒绝规则，禁用并降低相关偏好权重
            rule = rule_engine.get_rule(rule_id)
            if rule:
                rule_engine.disable_rule(rule_id)

event_collector = EventCollector()
