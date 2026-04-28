import os
import tempfile
from datetime import datetime
from unittest.mock import Mock
from cognix.core.skills_manager import SkillsManager

def test_skill_creation():
    """测试技能创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SkillsManager(skills_dir=tmpdir)
        
        skill = manager.create_skill(
            name="weekly_report",
            description="每周五生成周报",
            trigger="friday_17_00",
            steps=[
                "拉取本周项目进展",
                "汇总blocker",
                "生成周报",
                "发送默认收件人"
            ]
        )
        
        assert skill['name'] == "weekly_report"
        assert skill['trigger'] == "friday_17_00"
        assert len(skill['steps']) == 4
        assert "拉取本周项目进展" in skill['steps']
        
        # 验证文件创建
        skill_file = os.path.join(tmpdir, "weekly_report.yaml")
        assert os.path.exists(skill_file)

def test_load_skills():
    """测试加载技能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SkillsManager(skills_dir=tmpdir)
        
        # 创建两个技能
        manager.create_skill(
            name="skill1",
            description="测试技能1",
            trigger="daily_09_00",
            steps=["步骤1", "步骤2"]
        )
        
        manager.create_skill(
            name="skill2",
            description="测试技能2",
            trigger="weekly_monday",
            steps=["步骤A", "步骤B", "步骤C"]
        )
        
        skills = manager.list_skills()
        
        assert len(skills) == 2
        skill_names = [s['name'] for s in skills]
        assert "skill1" in skill_names
        assert "skill2" in skill_names

def test_check_repeat_pattern():
    """测试重复模式检测"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SkillsManager(skills_dir=tmpdir)
        
        # 检测重复性
        task_history = [
            {"task_type": "周报", "tool_calls": 6, "timestamp": "2026-04-21"},
            {"task_type": "周报", "tool_calls": 5, "timestamp": "2026-04-14"},
            {"task_type": "周报", "tool_calls": 7, "timestamp": "2026-04-07"}
        ]
        
        result = manager.check_repeat_pattern(task_history)
        
        assert result['should_save'] == True
        assert "同类任务重复" in result['reason']
        assert result['confidence'] >= 0.5

def test_suggest_skill():
    """测试建议保存技能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SkillsManager(skills_dir=tmpdir)
        
        steps = ["打开文档", "编辑内容", "保存"]
        suggestion = manager.suggest_skill(steps, "文档编辑")
        
        assert suggestion['suggested'] == True
        assert suggestion['name'] == "文档编辑"
        assert len(suggestion['steps']) == 3

def test_execute_skill():
    """测试执行技能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SkillsManager(skills_dir=tmpdir)
        
        manager.create_skill(
            name="test_skill",
            description="测试技能",
            trigger="manual",
            steps=["步骤1", "步骤2"]
        )
        
        # Mock执行函数
        executed_steps = []
        def mock_executor(step):
            executed_steps.append(step)
            return {"success": True, "output": f"执行{step}"}
        
        result = manager.execute_skill("test_skill", executor=mock_executor)
        
        assert result['success'] == True
        assert len(executed_steps) == 2
        assert "步骤1" in executed_steps
        assert "步骤2" in executed_steps
