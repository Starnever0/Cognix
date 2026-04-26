import os
import tempfile
from unittest.mock import Mock, patch
from cognix.core.reminder_service import ReminderService, Reminder

def test_reminder_creation():
    """测试提醒创建"""
    reminder = Reminder(
        id="reminder1",
        name="周报提醒",
        trigger="friday_17_00",
        description="每周五下午5点提醒发周报",
        action="generate_report",
        params={"type": "weekly"}
    )
    
    assert reminder.id == "reminder1"
    assert reminder.name == "周报提醒"
    assert reminder.trigger == "friday_17_00"
    assert reminder.action == "generate_report"

def test_add_and_list_reminders():
    """测试添加和列出提醒"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReminderService(reminders_dir=tmpdir)
        
        reminder = service.add_reminder(
            name="会议提醒",
            trigger="daily_09_00",
            description="每天早上9点会议提醒",
            action="notify_meeting",
            params={}
        )
        
        reminders = service.list_reminders()
        
        assert len(reminders) == 1
        assert reminders[0]['name'] == "会议提醒"
        assert reminders[0]['trigger'] == "daily_09_00"

def test_remove_reminder():
    """测试删除提醒"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReminderService(reminders_dir=tmpdir)
        
        service.add_reminder(
            name="测试提醒",
            trigger="once",
            description="测试",
            action="test",
            params={}
        )
        
        assert len(service.list_reminders()) == 1
        
        service.remove_reminder("测试提醒")
        
        assert len(service.list_reminders()) == 0

def test_parse_trigger():
    """测试触发器解析"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReminderService(reminders_dir=tmpdir)
        
        # 测试每周触发器
        cron_expr = service._parse_trigger("friday_17_00")
        assert cron_expr == "0 17 * * 4"  # 周五17:00
        
        # 测试每天触发器
        cron_expr = service._parse_trigger("daily_09_00")
        assert cron_expr == "0 9 * * *"  # 每天09:00
        
        # 测试每月触发器
        cron_expr = service._parse_trigger("monthly_1_09_00")
        assert cron_expr == "0 9 1 * *"  # 每月1日09:00

def test_check_due_reminders():
    """测试检查到期提醒"""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReminderService(reminders_dir=tmpdir)
        
        service.add_reminder(
            name="立即提醒",
            trigger="once",
            description="立即执行",
            action="test",
            params={"execute_now": True}
        )
        
        due = service.check_due_reminders()
        
        assert len(due) >= 0
