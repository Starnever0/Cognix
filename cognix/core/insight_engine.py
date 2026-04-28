from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
from cognix.core.habit_extractor import get_habit_extractor
from cognix.core.skills_manager import SkillsManager
from cognix.core.memory_system import get_memory_system
from cognix.utils.config import config

class InsightEngine:
    """
    主动洞察反馈引擎
    基于用户记忆、习惯、技能库，主动生成有价值的建议、提醒、推荐和预警
    """
    
    INSIGHT_TYPES = {
        "optimization": "优化建议",
        "reminder": "事项提醒",
        "skill_recommendation": "技能推荐",
        "risk_warning": "风险预警"
    }
    
    def __init__(self):
        self.habit_extractor = get_habit_extractor()
        self.skills_manager = SkillsManager()
        self.memory_system = get_memory_system()
        self.insights = []  # 存储生成的洞察结果
        
    def generate_insights(self) -> List[Dict]:
        """
        生成所有类型的洞察结果
        :return: 洞察列表，包含类型、内容、优先级、建议行动
        """
        self.insights = []
        
        # 生成各类洞察
        self._generate_optimization_suggestions()
        self._generate_reminders()
        self._generate_skill_recommendations()
        self._generate_risk_warnings()
        
        # 按优先级排序，高优先级在前
        self.insights.sort(key=lambda x: x["priority"], reverse=True)
        return self.insights
    
    def _generate_optimization_suggestions(self):
        """生成习惯优化建议"""
        habits = self.habit_extractor.get_user_habits(min_confidence=0.7, min_occur_count=3)
        
        for habit in habits:
            content = habit["content"]
            category = habit["category"]
            
            # 识别可以自动化的办公习惯
            if category == "office":
                # 每周/每月重复的手动任务可以建议自动化
                if re.search(r"每周|每月|每天|定期", content) and re.search(r"写|整理|汇总|发送|提交", content):
                    # 检查是否已有相关技能
                    has_skill = any(
                        re.search(r"周报|报告|汇总|发送", skill["name"]) 
                        for skill in self.skills_manager.list_skills()
                    )
                    
                    if not has_skill:
                        self.insights.append({
                            "type": "optimization",
                            "type_name": self.INSIGHT_TYPES["optimization"],
                            "content": f"检测到你有重复手动任务：「{content}」，建议创建自动化技能来完成，预计每次可节省10-30分钟",
                            "priority": 2,
                            "suggested_action": "自动生成对应工作流技能",
                            "related_habit": habit["id"]
                        })
            
            # 识别低效的工作流程
            if category == "behavior" and "手动" in content or "每次都要" in content:
                self.insights.append({
                    "type": "optimization",
                    "type_name": self.INSIGHT_TYPES["optimization"],
                    "content": f"检测到你有低效率操作习惯：「{content}」，可以考虑优化工作流程",
                    "priority": 1,
                    "suggested_action": "分析优化路径",
                    "related_habit": habit["id"]
                })
    
    def _generate_reminders(self):
        """生成周期性事项提醒"""
        habits = self.habit_extractor.get_user_habits(category="office", min_confidence=0.8)
        now = datetime.now()
        
        for habit in habits:
            content = habit["content"]
            
            # 每周一的提醒
            if re.search(r"每周一|周一上午|周会|周报", content) and now.weekday() == 0:  # 0是周一
                time_match = re.search(r"(\d{1,2})[:：](\d{1,2})", content)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # 提前1小时提醒
                    if event_time - timedelta(hours=1) <= now <= event_time:
                        self.insights.append({
                            "type": "reminder",
                            "type_name": self.INSIGHT_TYPES["reminder"],
                            "content": f"提醒：你习惯「{content}」，现在距离开始还有不到1小时",
                            "priority": 3,
                            "suggested_action": "准备相关材料",
                            "related_habit": habit["id"]
                        })
            
            # 每月固定日期的提醒
            monthly_match = re.search(r"每月(\d{1,2})号", content)
            if monthly_match:
                day = int(monthly_match.group(1))
                if now.day == day:
                    self.insights.append({
                        "type": "reminder",
                        "type_name": self.INSIGHT_TYPES["reminder"],
                        "content": f"提醒：今天是每月{day}号，你需要完成「{content}」",
                        "priority": 3,
                        "suggested_action": "按时完成该任务",
                        "related_habit": habit["id"]
                    })
            
            # 周报提醒：每周五下午
            if "周报" in content and now.weekday() == 4 and now.hour >= 14:  # 4是周五
                self.insights.append({
                    "type": "reminder",
                    "type_name": self.INSIGHT_TYPES["reminder"],
                    "content": "提醒：周五了，记得准备本周周报",
                    "priority": 2,
                    "suggested_action": "生成周报",
                    "related_habit": habit["id"]
                })
    
    def _generate_skill_recommendations(self):
        """生成适合当前场景的技能推荐"""
        # 最近的记忆内容
        recent_memories = self.memory_system.search_memory("", limit=20)
        skills = self.skills_manager.list_skills()
        
        if not recent_memories or not skills:
            return
        
        recent_content = " ".join([m.get("content", "") + m.get("heading", "") for m in recent_memories]).lower()
        
        for skill in skills:
            skill_name = skill["name"].lower()
            skill_desc = skill.get("description", "").lower()
            skill_steps = " ".join(skill.get("steps", [])).lower()
            
            # 计算技能和最近内容的匹配度
            match_score = 0
            if skill_name in recent_content:
                match_score += 3
            if any(word in recent_content for word in skill_desc.split()):
                match_score += 2
            if any(step in recent_content for step in skill_steps.split()):
                match_score += 1
            
            if match_score >= 2:
                self.insights.append({
                    "type": "skill_recommendation",
                    "type_name": self.INSIGHT_TYPES["skill_recommendation"],
                    "content": f"推荐使用技能「{skill['name']}」来完成当前任务，该技能可以实现：{skill['description']}",
                    "priority": 2,
                    "suggested_action": f"直接调用技能 {skill['name']}",
                    "related_skill": skill["name"]
                })
    
    def _generate_risk_warnings(self):
        """生成操作风险预警"""
        # 最近的操作内容
        recent_memories = self.memory_system.search_memory("", limit=10)
        feedback_habits = self.habit_extractor.get_user_habits(category="feedback", min_confidence=0.8)
        
        if not recent_memories:
            return
        
        recent_content = " ".join([m.get("content", "") + m.get("heading", "") for m in recent_memories]).lower()
        
        # 检测和用户反馈习惯冲突的操作
        for habit in feedback_habits:
            habit_content = habit["content"].lower()
            
            # 识别禁止类操作
            if re.search(r"不要|别|禁止|不允许", habit_content):
                # 提取禁止的内容
                forbidden_pattern = re.sub(r"不要|别|禁止|不允许", "", habit_content).strip()
                if forbidden_pattern and forbidden_pattern in recent_content:
                    self.insights.append({
                        "type": "risk_warning",
                        "type_name": self.INSIGHT_TYPES["risk_warning"],
                        "content": f"风险预警：你当前的操作可能违反了之前的反馈习惯：「{habit['content']}」",
                        "priority": 3,
                        "suggested_action": "确认是否继续执行该操作",
                        "related_habit": habit["id"]
                    })
        
        # 非工作时间操作生产环境的风险
        if now.hour < 9 or now.hour > 19 or now.weekday() >= 5:  # 非工作时间或周末
            if "生产环境" in recent_content or "线上" in recent_content or "部署" in recent_content:
                self.insights.append({
                    "type": "risk_warning",
                    "type_name": self.INSIGHT_TYPES["risk_warning"],
                    "content": "风险预警：当前是非工作时间，操作生产环境请谨慎确认",
                    "priority": 3,
                    "suggested_action": "确认操作必要性，建议工作日工作时间执行",
                    "related_habit": None
                })
    
    def get_latest_insights(self, limit: int = 5, insight_type: str = None) -> List[Dict]:
        """获取最新的洞察结果"""
        if not self.insights:
            self.generate_insights()
        
        filtered = self.insights
        if insight_type:
            filtered = [i for i in filtered if i["type"] == insight_type]
        
        return filtered[:limit]


# 全局实例
_insight_engine_instance: Optional[InsightEngine] = None

def get_insight_engine() -> InsightEngine:
    """获取全局洞察引擎实例"""
    global _insight_engine_instance
    if _insight_engine_instance is None:
        _insight_engine_instance = InsightEngine()
    return _insight_engine_instance
