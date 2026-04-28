from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
import json
from pathlib import Path
from cognix.core.skills_manager import SkillsManager
from cognix.utils.config import config

class SkillEvolution:
    """
    技能自我进化模块
    参考Hermes Agent设计，实现技能自动生成、自我优化、版本管理全流程
    """
    
    def __init__(self, skills_manager: Optional[SkillsManager] = None):
        self.skills_manager = skills_manager or SkillsManager()
        self.min_similarity = 0.8  # 任务相似度阈值
        self.min_success_rate = 0.8  # 技能最低上线成功率
        self.max_inactive_days = 90  # 技能最大未使用天数，超过自动归档
        
    def generate_skill_from_trajectory(self, trajectory: Dict) -> Optional[Dict]:
        """
        从任务执行轨迹自动生成技能
        :param trajectory: 执行轨迹，包含task_name, task_type, steps, tool_calls, success, execution_log
        :return: 生成的技能字典，生成失败返回None
        """
        # 只有成功执行的任务才能生成技能
        if not trajectory.get("success", False):
            return None
        
        task_name = trajectory.get("task_name", "")
        task_type = trajectory.get("task_type", "workflow")
        steps = trajectory.get("steps", [])
        tool_calls = trajectory.get("tool_calls", [])
        
        if not steps and not tool_calls:
            return None
        
        # 生成标准化步骤
        normalized_steps = self._normalize_steps(steps, tool_calls)
        if len(normalized_steps) < 2:
            return None  # 步骤太少不需要生成技能
        
        # 生成技能名称和描述
        skill_name = self._generate_skill_name(task_name, task_type, normalized_steps)
        skill_description = self._generate_skill_description(task_name, normalized_steps)
        
        # 检查是否已存在相似技能
        existing_skill = self._find_similar_skill(skill_description, normalized_steps)
        if existing_skill:
            # 已有相似技能，更新优化而不是新建
            return self._update_existing_skill(existing_skill, trajectory)
        
        # 创建新技能
        skill = self.skills_manager.create_skill(
            name=skill_name,
            description=skill_description,
            trigger="manual",  # 默认手动触发，后续可以自动识别触发条件
            steps=normalized_steps
        )
        
        # 添加进化相关元数据
        skill.update({
            "version": "1.0.0",
            "success_rate": 1.0,
            "call_count": 0,
            "success_count": 0,
            "last_executed": None,
            "created_from_trajectory": trajectory.get("id", ""),
            "auto_generated": True
        })
        
        self.skills_manager.update_skill(skill_name, **skill)
        return skill
    
    def record_execution_result(self, skill_name: str, success: bool, execution_log: Dict = None) -> Optional[Dict]:
        """
        记录技能执行结果，用于后续优化
        :param skill_name: 技能名称
        :param success: 执行是否成功
        :param execution_log: 执行日志
        :return: 更新后的技能
        """
        skill = self.skills_manager.load_skill(skill_name)
        if not skill:
            return None
        
        # 更新统计数据
        call_count = skill.get("call_count", 0) + 1
        success_count = skill.get("success_count", 0) + (1 if success else 0)
        success_rate = success_count / call_count
        
        update_data = {
            "call_count": call_count,
            "success_count": success_count,
            "success_rate": success_rate,
            "last_executed": datetime.now().isoformat()
        }
        
        # 如果成功率低于阈值，自动标记为待优化
        if success_rate < self.min_success_rate and call_count >= 5:
            update_data["need_optimization"] = True
            update_data["enabled"] = False  # 自动下线低成功率技能
        
        return self.skills_manager.update_skill(skill_name, **update_data)
    
    def optimize_skill(self, skill_name: str, execution_logs: List[Dict] = None) -> Optional[Dict]:
        """
        基于执行日志优化技能
        :param skill_name: 技能名称
        :param execution_logs: 历史执行日志，默认加载最近10次执行记录
        :return: 优化后的技能
        """
        skill = self.skills_manager.load_skill(skill_name)
        if not skill:
            return None
        
        # 获取执行日志，如果没有传入则加载历史记录（后续实现）
        if not execution_logs:
            execution_logs = []
        
        current_steps = skill.get("steps", [])
        optimized = False
        
        # 优化1：移除重复步骤
        unique_steps = []
        seen_steps = set()
        for step in current_steps:
            step_normalized = re.sub(r'\s+', ' ', step.strip().lower())
            if step_normalized not in seen_steps:
                seen_steps.add(step_normalized)
                unique_steps.append(step)
            else:
                optimized = True
        
        if optimized:
            skill["steps"] = unique_steps
        
        # 优化2：调整步骤顺序（基于成功执行的顺序统计）
        # 后续可以基于执行日志的步骤耗时、成功率优化顺序
        
        # 版本号升级：小版本号+1
        current_version = skill.get("version", "1.0.0")
        version_parts = current_version.split('.')
        if len(version_parts) == 3:
            new_version = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"
        else:
            new_version = "1.0.1"
        
        update_data = {
            "steps": skill["steps"],
            "version": new_version,
            "need_optimization": False,
            "enabled": True,  # 优化后重新启用
            "success_rate": 1.0,  # 优化后重置成功率统计
            "call_count": 0,
            "success_count": 0
        }
        
        return self.skills_manager.update_skill(skill_name, **update_data)
    
    def cleanup_inactive_skills(self) -> int:
        """
        清理长期未使用的技能，自动归档
        :return: 清理的技能数量
        """
        skills = self.skills_manager.list_skills()
        cleaned = 0
        cutoff_date = datetime.now() - timedelta(days=self.max_inactive_days)
        
        for skill in skills:
            last_executed = skill.get("last_executed")
            if not last_executed:
                # 从未执行过的技能，创建超过30天也清理
                created_at = skill.get("created_at")
                if created_at:
                    try:
                        created_date = datetime.fromisoformat(created_at)
                        if created_date < cutoff_date:
                            self.skills_manager.delete_skill(skill["name"])
                            cleaned += 1
                    except:
                        pass
            else:
                try:
                    last_executed_date = datetime.fromisoformat(last_executed)
                    if last_executed_date < cutoff_date:
                        self.skills_manager.delete_skill(skill["name"])
                        cleaned += 1
                except:
                    pass
        
        return cleaned
    
    def _run_skill_evolution(self) -> dict:
        """执行技能进化流程：技能清理、自动生成技能、优化、去重"""
        # 清理长期未使用的技能
        cleaned_inactive = self.cleanup_inactive_skills()
        
        # 清理重复僵尸技能
        duplicate_cleanup = self.cleanup_duplicate_skills()
        
        # 自动从历史任务中生成新技能
        new_skills = self.auto_generate_skills_from_history()
        
        # 自动优化需要优化的技能
        optimized = 0
        skills = self.skills_manager.list_skills()
        for skill in skills:
            if skill.get("need_optimization", False):
                self.optimize_skill(skill["name"])
                optimized += 1
        
        return {
            "cleaned_inactive": cleaned_inactive,
            "merged_duplicates": duplicate_cleanup["merged"],
            "deleted_duplicates": duplicate_cleanup["deleted"],
            "new_auto_generated": len(new_skills),
            "optimized": optimized
        }
    
    def auto_generate_skills_from_history(self, days: int = 30) -> List[Dict]:
        """
        自动从历史任务轨迹中识别重复模式，生成技能
        :param days: 分析最近多少天的任务历史
        :return: 新生成的技能列表
        """
        # 获取最近的任务执行历史（后续对接任务历史存储）
        # 目前通过记忆系统搜索相关任务记录
        from cognix.core.memory_system import get_memory_system
        memory_system = get_memory_system()
        memories = memory_system.search_memory("", limit=200)
        
        # 提取任务轨迹
        task_trajectories = self._extract_task_trajectories(memories)
        
        # 检测重复模式
        pattern_results = self.skills_manager.check_repeat_pattern(task_trajectories)
        
        new_skills = []
        if pattern_results["should_save"]:
            # 过滤出对应类型的任务
            task_type = pattern_results["task_type"]
            relevant_tasks = [t for t in task_trajectories if t.get("task_type") == task_type]
            
            if relevant_tasks:
                # 取最新的成功任务轨迹生成技能
                latest_task = max(relevant_tasks, key=lambda x: x.get("timestamp", 0))
                new_skill = self.generate_skill_from_trajectory(latest_task)
                if new_skill:
                    new_skills.append(new_skill)
        
        return new_skills
    
    def _extract_task_trajectories(self, memories: List[Dict]) -> List[Dict]:
        """从记忆中提取任务轨迹"""
        trajectories = []
        
        for mem in memories:
            content = mem.get("content", "") + "\n" + mem.get("heading", "")
            
            # 识别任务相关记忆
            if "任务" in content or "执行" in content or "工具调用" in content or "步骤" in content:
                # 提取步骤
                steps = re.findall(r'\d+\.\s*(.+)', content)
                if not steps:
                    steps = re.findall(r'-\s*(.+)', content)
                
                # 提取工具调用
                tool_calls = []
                tool_matches = re.findall(r'调用工具[:：]\s*(\w+)\((.*?)\)', content)
                for tool_name, params_str in tool_matches:
                    try:
                        params = {}
                        if params_str:
                            param_pairs = params_str.split(',')
                            for pair in param_pairs:
                                if '=' in pair:
                                    k, v = pair.split('=', 1)
                                    params[k.strip()] = v.strip()
                        tool_calls.append({"name": tool_name, "parameters": params})
                    except:
                        pass
                
                if steps or tool_calls:
                    # 推断任务类型
                    task_type = "unknown"
                    if "周报" in content:
                        task_type = "weekly_report"
                    elif "会议" in content:
                        task_type = "meeting"
                    elif "部署" in content or "上线" in content:
                        task_type = "deployment"
                    elif "测试" in content:
                        task_type = "testing"
                    
                    trajectories.append({
                        "id": mem.get("id", ""),
                        "task_name": mem.get("heading", f"{task_type}任务"),
                        "task_type": task_type,
                        "steps": steps,
                        "tool_calls": tool_calls,
                        "success": True,  # 存储在记忆中的默认是成功的
                        "timestamp": mem.get("created_at", datetime.now().isoformat())
                    })
        
        return trajectories
    
    def export_to_agentskills(self, skill_name: str, output_path: Optional[str] = None) -> Optional[Dict]:
        """
        导出技能为agentskills.io兼容格式
        :param skill_name: 技能名称
        :param output_path: 输出路径，默认保存到skills目录
        :return: 导出的技能数据
        """
        skill = self.skills_manager.load_skill(skill_name)
        if not skill:
            return None
        
        # agentskills.io标准格式
        agentskill = {
            "schema_version": "1.0",
            "name": skill["name"],
            "description": skill["description"],
            "author": "Cognix Autodream",
            "version": skill.get("version", "1.0.0"),
            "license": "MIT",
            "categories": ["workflow", "auto-generated"],
            "triggers": [
                {
                    "type": "manual",
                    "name": skill["name"],
                    "description": f"执行{skill['description']}"
                }
            ],
            "steps": skill["steps"],
            "parameters": {},
            "returns": {
                "type": "object",
                "description": "执行结果"
            },
            "auto_generated": True,
            "created_at": skill["created_at"]
        }
        
        if output_path is None:
            output_path = str(self.skills_manager.skills_dir / f"{skill_name}_agentskills.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(agentskill, f, ensure_ascii=False, indent=2)
        
        return agentskill
    
    def import_agentskills(self, file_path: str) -> Optional[Dict]:
        """
        从agentskills.io格式导入技能
        :param file_path: 技能文件路径
        :return: 导入的技能
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                agentskill = json.load(f)
            
            # 转换为Cognix格式
            skill_name = agentskill["name"]
            skill = self.skills_manager.create_skill(
                name=skill_name,
                description=agentskill["description"],
                trigger="manual",
                steps=agentskill["steps"]
            )
            
            skill.update({
                "version": agentskill.get("version", "1.0.0"),
                "author": agentskill.get("author", "community"),
                "imported_from_agentskills": True
            })
            
            self.skills_manager.update_skill(skill_name, **skill)
            return skill
        except Exception as e:
            return None
    
    def _normalize_steps(self, steps: List[str], tool_calls: List[Dict]) -> List[str]:
        """标准化步骤格式"""
        normalized = []
        
        # 先添加手动步骤
        for step in steps:
            step = re.sub(r'\d+\.\s*', '', step).strip()
            if step:
                normalized.append(step)
        
        # 再添加工具调用步骤
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            parameters = tool_call.get("parameters", {})
            if tool_name:
                param_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
                step = f"调用工具: {tool_name}({param_str})"
                normalized.append(step)
        
        return normalized
    
    def _generate_skill_name(self, task_name: str, task_type: str, steps: List[str] = None) -> str:
        """
        生成标准化的技能名称，基于功能指纹，减少随机性
        命名规则：[动作]_[操作对象]_[场景]，例如：generate_weekly_report, deploy_production_env
        """
        # 优先基于功能指纹生成标准化名称
        if steps:
            fp = self._extract_functional_fingerprint(task_name, steps)
            name_parts = []
            
            # 取第一个动作
            if fp["actions"]:
                name_parts.append(list(fp["actions"])[0])
            
            # 取第一个操作对象
            if fp["objects"]:
                name_parts.append(list(fp["objects"])[0])
            
            # 取第一个场景（如果有）
            if fp["scenes"]:
                scene = list(fp["scenes"])[0]
                # 排除常见通用词
                if scene not in ["自动化", "批量"]:
                    name_parts.append(scene)
            
            if name_parts:
                # 组合成标准化名称
                name = "_".join(name_parts).lower()
                # 中文替换为拼音？暂时保留中文，后续可以考虑拼音转换
                name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', name)
                if len(name) >= 3:  # 有效名称
                    # 确保唯一
                    counter = 1
                    base_name = name
                    while self.skills_manager.load_skill(name):
                        name = f"{base_name}_{counter}"
                        counter += 1
                    return name
        
        # 功能指纹提取失败时回退到原逻辑
        name_base = task_name if task_name else task_type
        name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', name_base).lower()
        name = name[:50] if len(name) > 50 else name
        
        # 确保名称唯一
        counter = 1
        base_name = name
        while self.skills_manager.load_skill(name):
            name = f"{base_name}_{counter}"
            counter += 1
        
        return name
    
    def cleanup_duplicate_skills(self) -> Dict:
        """
        清理重复的僵尸技能，合并功能相同的技能
        :return: 清理结果：merged=合并数量, deleted=删除数量
        """
        skills = self.skills_manager.list_skills()
        if len(skills) < 2:
            return {"merged": 0, "deleted": 0}
        
        merged_count = 0
        deleted_count = 0
        processed = set()
        
        for i, skill1 in enumerate(skills):
            if skill1["name"] in processed:
                continue
                
            # 查找所有和skill1相似的技能
            duplicates = []
            for j, skill2 in enumerate(skills[i+1:]):
                if skill2["name"] in processed:
                    continue
                    
                fp1 = self._extract_functional_fingerprint(skill1["description"], skill1["steps"])
                fp2 = self._extract_functional_fingerprint(skill2["description"], skill2["steps"])
                similarity = self._calculate_functional_similarity(fp1, fp2)
                
                if similarity >= 0.9:  # 相似度极高，判定为完全重复
                    duplicates.append(skill2)
            
            if duplicates:
                # 合并重复技能到主技能
                main_skill = skill1
                all_steps = main_skill["steps"].copy()
                total_calls = main_skill.get("call_count", 0)
                total_success = main_skill.get("success_count", 0)
                
                for dup in duplicates:
                    # 合并去重步骤
                    for step in dup["steps"]:
                        if step not in all_steps:
                            all_steps.append(step)
                    
                    # 合并统计数据
                    total_calls += dup.get("call_count", 0)
                    total_success += dup.get("success_count", 0)
                    
                    # 删除重复技能
                    self.skills_manager.delete_skill(dup["name"])
                    processed.add(dup["name"])
                    deleted_count += 1
                
                # 更新主技能
                update_data = {
                    "steps": all_steps,
                    "call_count": total_calls,
                    "success_count": total_success,
                    "success_rate": total_success / total_calls if total_calls > 0 else 1.0
                }
                self.skills_manager.update_skill(main_skill["name"], **update_data)
                merged_count += 1
                processed.add(main_skill["name"])
        
        return {
            "merged": merged_count,
            "deleted": deleted_count
        }
    
    def _generate_skill_description(self, task_name: str, steps: List[str]) -> str:
        """生成技能描述"""
        step_summary = "、".join(steps[:3])
        if len(steps) > 3:
            step_summary += f"等{len(steps)}个步骤"
        return f"{task_name}：{step_summary}"
    
    def _extract_functional_fingerprint(self, description: str, steps: List[str]) -> Dict:
        """
        提取技能的功能指纹，用于相似度匹配
        提取核心特征：动作、操作对象、使用工具、目标场景
        """
        content = (description + " " + " ".join(steps)).lower()
        
        # 核心动作关键词
        action_keywords = ["生成", "创建", "整理", "汇总", "发送", "部署", "测试", "检查", "分析", "提取", "同步", "备份", "恢复"]
        actions = [kw for kw in action_keywords if kw in content]
        
        # 操作对象关键词
        object_keywords = ["周报", "报告", "会议纪要", "代码", "文档", "数据", "数据库", "服务器", "配置", "环境", "任务", "流程"]
        objects = [kw for kw in object_keywords if kw in content]
        
        # 使用的工具集合
        tool_keywords = ["调用工具", "执行命令", "访问", "查询", "调用"]
        tools = []
        for step in steps:
            tool_match = re.search(r'调用工具[:：]\s*(\w+)', step.lower())
            if tool_match:
                tools.append(tool_match.group(1))
        
        # 场景关键词
        scene_keywords = ["每周", "每月", "每天", "定时", "自动化", "批量", "线上", "生产", "测试", "开发"]
        scenes = [kw for kw in scene_keywords if kw in content]
        
        return {
            "actions": set(actions),
            "objects": set(objects),
            "tools": set(tools),
            "scenes": set(scenes),
            "step_count": len(steps)
        }
    
    def _calculate_functional_similarity(self, fp1: Dict, fp2: Dict) -> float:
        """计算两个技能功能指纹的相似度"""
        score = 0.0
        total_weight = 0.0
        
        # 动作匹配（权重最高，决定技能的核心目的）
        weight = 0.35
        total_weight += weight
        if fp1["actions"] and fp2["actions"]:
            action_inter = fp1["actions"].intersection(fp2["actions"])
            action_union = fp1["actions"].union(fp2["actions"])
            score += weight * (len(action_inter) / len(action_union)) if action_union else 0
        
        # 操作对象匹配（权重次高，决定技能的处理对象）
        weight = 0.3
        total_weight += weight
        if fp1["objects"] and fp2["objects"]:
            obj_inter = fp1["objects"].intersection(fp2["objects"])
            obj_union = fp1["objects"].union(fp2["objects"])
            score += weight * (len(obj_inter) / len(obj_union)) if obj_union else 0
        
        # 工具集合匹配（权重中等，决定技能的实现方式）
        weight = 0.2
        total_weight += weight
        if fp1["tools"] and fp2["tools"]:
            tool_inter = fp1["tools"].intersection(fp2["tools"])
            tool_union = fp1["tools"].union(fp2["tools"])
            score += weight * (len(tool_inter) / len(tool_union)) if tool_union else 0
        
        # 场景匹配（权重较低，决定技能的使用场景）
        weight = 0.1
        total_weight += weight
        if fp1["scenes"] and fp2["scenes"]:
            scene_inter = fp1["scenes"].intersection(fp2["scenes"])
            scene_union = fp1["scenes"].union(fp2["scenes"])
            score += weight * (len(scene_inter) / len(scene_union)) if scene_union else 0
        
        # 步骤数量匹配（权重最低，步骤数差异过大则不是同一个技能）
        weight = 0.05
        total_weight += weight
        step_diff = abs(fp1["step_count"] - fp2["step_count"])
        if step_diff <= 2:
            score += weight
        elif step_diff <= 4:
            score += weight * 0.5
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _find_similar_skill(self, description: str, steps: List[str]) -> Optional[Dict]:
        """查找相似的现有技能，使用功能指纹+步骤文本双重匹配"""
        skills = self.skills_manager.list_skills()
        if not skills:
            return None
        
        # 提取新技能的功能指纹
        new_fp = self._extract_functional_fingerprint(description, steps)
        new_steps_set = set(re.sub(r'\s+', ' ', s.lower()) for s in steps)
        
        max_similarity = 0.0
        most_similar = None
        
        for skill in skills:
            skill_steps = skill.get("steps", [])
            skill_desc = skill.get("description", "")
            
            # 1. 计算功能指纹相似度
            skill_fp = self._extract_functional_fingerprint(skill_desc, skill_steps)
            func_similarity = self._calculate_functional_similarity(new_fp, skill_fp)
            
            # 2. 计算步骤文本相似度
            skill_steps_set = set(re.sub(r'\s+', ' ', s.lower()) for s in skill_steps)
            text_similarity = 0.0
            if new_steps_set and skill_steps_set:
                intersection = new_steps_set.intersection(skill_steps_set)
                union = new_steps_set.union(skill_steps_set)
                text_similarity = len(intersection) / len(union) if union else 0.0
            
            # 综合相似度：功能相似度占70%，文本相似度占30%
            total_similarity = func_similarity * 0.7 + text_similarity * 0.3
            
            # 超过阈值则认为是相似技能，选相似度最高的
            if total_similarity >= self.min_similarity and total_similarity > max_similarity:
                max_similarity = total_similarity
                most_similar = skill
        
        return most_similar
    
    def _update_existing_skill(self, skill: Dict, trajectory: Dict) -> Dict:
        """更新现有技能，融合新的执行轨迹"""
        # 合并步骤，去重
        existing_steps = skill.get("steps", [])
        new_steps = self._normalize_steps(trajectory.get("steps", []), trajectory.get("tool_calls", []))
        
        # 合并去重
        combined_steps = []
        seen = set()
        for step in existing_steps + new_steps:
            normalized = re.sub(r'\s+', ' ', step.lower())
            if normalized not in seen:
                seen.add(normalized)
                combined_steps.append(step)
        
        # 小版本升级
        current_version = skill.get("version", "1.0.0")
        version_parts = current_version.split('.')
        new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}.0" if len(version_parts) == 3 else "1.1.0"
        
        update_data = {
            "steps": combined_steps,
            "version": new_version,
            "success_rate": 1.0,  # 更新后重置成功率
            "call_count": 0,
            "success_count": 0
        }
        
        return self.skills_manager.update_skill(skill["name"], **update_data)


# 全局实例
_skill_evolution_instance: Optional[SkillEvolution] = None

def get_skill_evolution() -> SkillEvolution:
    """获取全局技能进化实例"""
    global _skill_evolution_instance
    if _skill_evolution_instance is None:
        _skill_evolution_instance = SkillEvolution()
    return _skill_evolution_instance
