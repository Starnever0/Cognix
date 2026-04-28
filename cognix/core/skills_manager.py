import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

class SkillsManager:
    """
    工作流沉淀模块（Skills Manager）
    自动识别用户重复行为，沉淀为可复用工作流
    
    触发路径：
    1. 实时识别：多步骤执行、涉及多个工具、明显重复性、用户表达"以后都这样做"
    2. 后台归纳：同类任务重复≥3次、单次任务工具调用≥5次、固定时间周期性发生
    """
    
    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir:
            self.skills_dir = Path(skills_dir)
        else:
            from cognix.utils.config import config
            self.skills_dir = config.home_path / "memory" / "skills"
        
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # 重复性检测阈值
        self.repeat_threshold = 3  # 同类任务重复次数阈值
        self.tool_call_threshold = 5  # 单次任务工具调用次数阈值
    
    def create_skill(self, name: str, description: str, trigger: str, steps: List[str]) -> Dict:
        """
        创建新技能
        :param name: 技能名称（唯一标识）
        :param description: 技能描述
        :param trigger: 触发条件（如 friday_17_00, daily_09_00, manual）
        :param steps: 步骤列表
        :return: 创建的技能字典
        """
        skill = {
            "name": name,
            "description": description,
            "trigger": trigger,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "enabled": True
        }
        
        # 保存到YAML文件
        file_path = self.skills_dir / f"{name}.yaml"
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(skill, f, default_flow_style=False, allow_unicode=True)
        
        return skill
    
    def load_skill(self, name: str) -> Optional[Dict]:
        """
        加载技能
        :param name: 技能名称
        :return: 技能字典，如果不存在返回None
        """
        file_path = self.skills_dir / f"{name}.yaml"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return None
    
    def list_skills(self) -> List[Dict]:
        """
        获取所有技能列表
        :return: 技能列表
        """
        skills = []
        for yaml_file in self.skills_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    skill = yaml.safe_load(f)
                    skills.append(skill)
            except Exception:
                pass
        
        return sorted(skills, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def update_skill(self, name: str, **kwargs) -> Optional[Dict]:
        """
        更新技能
        :param name: 技能名称
        :param kwargs: 要更新的字段
        :return: 更新后的技能字典，如果不存在返回None
        """
        skill = self.load_skill(name)
        if not skill:
            return None
        
        skill.update(kwargs)
        skill['updated_at'] = datetime.now().isoformat()
        
        file_path = self.skills_dir / f"{name}.yaml"
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(skill, f, default_flow_style=False, allow_unicode=True)
        
        return skill
    
    def delete_skill(self, name: str) -> bool:
        """
        删除技能
        :param name: 技能名称
        :return: 是否删除成功
        """
        file_path = self.skills_dir / f"{name}.yaml"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def check_repeat_pattern(self, task_history: List[Dict]) -> Dict:
        """
        检测重复模式
        :param task_history: 任务历史列表，每个元素包含task_type, tool_calls, timestamp
        :return: 检测结果，包含should_save, reason, confidence
        """
        if not task_history:
            return {"should_save": False, "reason": "无任务历史", "confidence": 0.0}
        
        # 统计各任务类型的重复次数
        type_counts = {}
        for task in task_history:
            task_type = task.get("task_type", "unknown")
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
        
        # 检查是否有重复超过阈值的任务类型
        for task_type, count in type_counts.items():
            if count >= self.repeat_threshold:
                # 检查单次工具调用次数
                avg_tool_calls = sum(
                    t.get("tool_calls", 0) for t in task_history 
                    if t.get("task_type") == task_type
                ) / count
                
                confidence = min(count / 10 + avg_tool_calls / 20, 1.0)
                
                if avg_tool_calls >= self.tool_call_threshold:
                    return {
                        "should_save": True,
                        "reason": f"同类任务重复{count}次，单次平均工具调用{avg_tool_calls:.1f}次",
                        "confidence": confidence,
                        "task_type": task_type
                    }
                else:
                    return {
                        "should_save": True,
                        "reason": f"同类任务重复超过{self.repeat_threshold}次",
                        "confidence": confidence,
                        "task_type": task_type
                    }
        
        return {"should_save": False, "reason": "未达到重复阈值", "confidence": 0.0}
    
    def suggest_skill(self, steps: List[str], task_type: str = "workflow") -> Dict:
        """
        根据执行步骤建议创建技能
        :param steps: 执行步骤列表
        :param task_type: 任务类型
        :return: 建议结果
        """
        # 生成技能名称
        name = task_type.lower().replace(" ", "_").replace("-", "_")
        
        # 检查是否已存在
        if self.load_skill(name):
            name = f"{name}_{int(datetime.now().timestamp())}"
        
        return {
            "suggested": True,
            "name": name,
            "description": f"{task_type}工作流",
            "steps": steps,
            "estimated_savings": f"约{len(steps)*2}分钟/次"
        }
    
    def execute_skill(self, name: str, executor: Optional[Callable] = None) -> Dict:
        """
        执行技能
        :param name: 技能名称
        :param executor: 步骤执行函数，接收步骤返回执行结果
        :return: 执行结果
        """
        skill = self.load_skill(name)
        if not skill:
            return {"success": False, "error": "技能不存在"}
        
        if not skill.get("enabled", True):
            return {"success": False, "error": "技能已禁用"}
        
        results = []
        success = True
        
        for step in skill.get("steps", []):
            try:
                if executor:
                    result = executor(step)
                else:
                    result = {"success": True, "step": step, "output": f"执行步骤: {step}"}
                
                results.append(result)
                
                if not result.get("success", True):
                    success = False
                    break
            except Exception as e:
                results.append({"success": False, "step": step, "error": str(e)})
                success = False
                break
        
        return {
            "success": success,
            "skill_name": name,
            "results": results,
            "total_steps": len(skill.get("steps", [])),
            "completed_steps": len(results)
        }


# 全局实例
_skills_manager_instance: Optional[SkillsManager] = None

def get_skills_manager() -> SkillsManager:
    """获取全局技能管理器实例"""
    global _skills_manager_instance
    if _skills_manager_instance is None:
        _skills_manager_instance = SkillsManager()
    return _skills_manager_instance
