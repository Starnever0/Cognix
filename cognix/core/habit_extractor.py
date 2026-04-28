from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import re
from collections import defaultdict
from cognix.core.memory_system import get_memory_system
from cognix.storage.sqlite_store import sqlite_store
from cognix.utils.config import config

class HabitExtractor:
    """
    用户习惯自动提取引擎
    从交互记录中识别用户的办公习惯、使用偏好、行为模式、反馈习惯等
    """
    
    # 习惯分类关键词映射
    HABIT_CATEGORIES = {
        "office": [
            "周报", "会议", "开会", "发送给", "发给", "抄送", "收件人",
            "每周", "每月", "每天", "定期", "流程", "习惯", "工作流",
            "报销", "审批", "待办", "任务", "日程", "日历", "提醒",
            "几点", "之前", "之后", "固定", "惯例", "报告", "汇总",
            "同步", "对齐", "评审", "复盘", "例会"
        ],
        "preference": [
            "默认", "设置", "偏好", "喜欢", "总是", "永远", "格式",
            "视图", "通知", "静音", "模板", "输出", "展示", "显示",
            "用什么格式", "用什么模式", "我习惯", "我一般", "我通常",
            "语言", "中文", "英文", "字体", "主题", "配色", "布局"
        ],
        "behavior": [
            "每次", "总是", "每次都", "我都会", "我一般会", "习惯先",
            "先做", "再做", "然后", "步骤", "顺序", "流程", "规律",
            "高频操作", "常用命令", "快捷键", "工具", "软件", "网站"
        ],
        "feedback": [
            "以后", "应该", "需要", "要", "不要", "别", "建议", "最好",
            "应该要", "应该是", "不对", "错了", "纠正", "修正", "问题",
            "下次", "注意", "改", "调整", "改进", "回答", "回复",
            "请你", "麻烦你", "希望你", "记得", "别忘了"
        ]
    }
    
    # 时序模式正则表达式
    TIME_PATTERNS = [
        r"每周(一|二|三|四|五|六|日|周.)\s*(上午|下午|晚上)?\s*(\d{1,2}[:：.]\d{1,2})?",
        r"每月(\d{1,2})号\s*(上午|下午|晚上)?\s*(\d{1,2}[:：.]\d{1,2})?",
        r"每天\s*(上午|下午|晚上)?\s*(\d{1,2}[:：.]\d{1,2})?",
        r"每(天|周|月|季度|年)",
        r"(\d{1,2})[:：.]\d{1,2}\s*(之前|之后)",
    ]
    
    def __init__(self, memory_system = None, store = None):
        self.memory_system = memory_system or get_memory_system()
        self.store = store or sqlite_store
        self.min_occur_threshold = 3  # 至少出现3次才判定为习惯
        self.min_confidence = 0.6  # 最低置信度阈值
    
    def extract_habits(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """
        从指定时间范围内的交互记录中提取用户习惯
        :param time_range: 时间范围，默认最近30天
        :return: 识别到的习惯列表
        """
        if time_range is None:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)
            time_range = (start_time, end_time)
        
        # 获取该时间段内的所有记忆
        memories = self._get_memories_in_range(time_range)
        habits = []
        
        for memory in memories:
            content = memory.get("content", "") + "\n" + memory.get("heading", "")
            content_lower = content.lower()
            
            # 识别分类
            category = self._classify_habit(content_lower)
            if not category:
                continue
            
            # 提取习惯内容
            habit_contents = self._extract_habit_content(content, category)
            for habit_content in habit_contents:
                if not habit_content or len(habit_content) < 10:
                    continue
                
                # 计算置信度
                confidence = self._calculate_confidence(habit_content, category, content)
                
                if confidence >= self.min_confidence:
                    habits.append({
                        "category": category,
                        "content": habit_content,
                        "confidence": confidence,
                        "metadata": {
                            "source_memory_id": memory.get("id"),
                            "source_content": content[:200]
                        }
                    })
        
        # 去重合并相同习惯
        merged_habits = self._merge_duplicate_habits(habits)
        
        # 只保留达到出现次数阈值的习惯
        final_habits = [
            h for h in merged_habits 
            if h["occur_count"] >= self.min_occur_threshold
        ]
        
        # 保存到数据库
        for habit in final_habits:
            self.store.add_habit(
                category=habit["category"],
                content=habit["content"],
                confidence=habit["confidence"],
                occur_count=habit["occur_count"],
                metadata=habit["metadata"]
            )
        
        return final_habits
    
    def _get_memories_in_range(self, time_range: Tuple[datetime, datetime]) -> List[Dict]:
        """获取指定时间范围内的所有记忆"""
        # 目前从记忆系统中搜索所有记忆，后续可以优化为按时间过滤
        return self.memory_system.search_memory("", limit=500)
    
    def _classify_habit(self, content_lower: str) -> Optional[str]:
        """根据内容分类习惯类型"""
        scores = {}
        for category, keywords in self.HABIT_CATEGORIES.items():
            score = 0
            for keyword in keywords:
                if keyword in content_lower:
                    score += 1
            scores[category] = score
        
        max_score = max(scores.values())
        if max_score == 0:
            return None
        
        # 返回得分最高的分类
        for category, score in scores.items():
            if score == max_score:
                return category
        
        return None
    
    def _extract_habit_content(self, content: str, category: str) -> List[str]:
        """从内容中提取具体的习惯描述"""
        habits = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # 移除markdown标记和特殊字符
            line = re.sub(r'[#*>`\-\[\]]', '', line).strip()
            
            # 包含时序模式的优先提取
            has_time_pattern = any(re.search(pattern, line) for pattern in self.TIME_PATTERNS)
            if has_time_pattern:
                habits.append(line)
                continue
            
            # 包含习惯关键词的提取
            habit_keywords = ["我习惯", "我一般", "我通常", "每次", "总是", "永远", "每次都", "我都会", "以后"]
            if any(keyword in line for keyword in habit_keywords):
                habits.append(line)
        
        return habits
    
    def _calculate_confidence(self, habit_content: str, category: str, full_content: str) -> float:
        """计算习惯识别的置信度"""
        confidence = 0.5  # 基础置信度
        
        # 包含明确的习惯关键词，+0.2
        habit_keywords = ["我习惯", "我一般", "我通常", "每次", "总是", "永远", "每次都", "我都会", "以后"]
        if any(keyword in habit_content for keyword in habit_keywords):
            confidence += 0.2
        
        # 包含时序模式，+0.15
        if any(re.search(pattern, habit_content) for pattern in self.TIME_PATTERNS):
            confidence += 0.15
        
        # 内容长度适中（10-100字），+0.1
        if 10 <= len(habit_content) <= 100:
            confidence += 0.1
        
        # 包含明确的动作描述，+0.05
        action_keywords = ["做", "写", "发", "开", "参加", "提交", "审批", "汇报", "整理"]
        if any(keyword in habit_content for keyword in action_keywords):
            confidence += 0.05
        
        return min(confidence, 0.95)  # 最高置信度不超过0.95
    
    def _merge_duplicate_habits(self, habits: List[Dict]) -> List[Dict]:
        """合并重复的习惯，统计出现次数"""
        habit_map = {}
        
        for habit in habits:
            content = habit["content"]
            # 简单去重：完全相同的内容合并
            if content in habit_map:
                habit_map[content]["occur_count"] += 1
                # 置信度取平均值
                habit_map[content]["confidence"] = (
                    habit_map[content]["confidence"] + habit["confidence"]
                ) / 2
            else:
                habit_map[content] = {
                    **habit,
                    "occur_count": 1
                }
        
        return list(habit_map.values())
    
    def detect_conflicting_habits(self) -> List[Dict]:
        """检测冲突的习惯"""
        habits = self.store.get_habits(min_confidence=0.6)
        conflicts = []
        
        # 反义词匹配规则
        opposite_pairs = [
            ("喜欢", "讨厌"), ("想要", "不要"), ("应该", "不应该"), 
            ("同意", "反对"), ("支持", "反对"), ("允许", "禁止"),
            ("开启", "关闭"), ("打开", "关闭"), ("启用", "禁用"),
            ("中文", "英文"), ("markdown", "表格"), ("简洁", "详细")
        ]
        
        for i, habit1 in enumerate(habits):
            for habit2 in habits[i+1:]:
                content1 = habit1["content"].lower()
                content2 = habit2["content"].lower()
                
                # 检测是否包含相反的表述
                has_conflict = False
                conflict_type = ""
                for pos, neg in opposite_pairs:
                    if (pos in content1 and neg in content2) or (neg in content1 and pos in content2):
                        # 检查是否描述的是同一事物
                        common_words = set(content1.split()) & set(content2.split())
                        if len(common_words) >= 2:
                            has_conflict = True
                            conflict_type = f"{pos}/{neg}冲突"
                            break
                
                if has_conflict:
                    conflicts.append({
                        "type": "conflict",
                        "conflict_type": conflict_type,
                        "habit1": habit1,
                        "habit2": habit2,
                        "suggestion": "请确认哪个习惯是正确的，标记为已验证"
                    })
        
        return conflicts
    
    def calibrate_confidence(self) -> int:
        """校准所有习惯的置信度，基于用户验证情况和出现频率"""
        habits = self.store.get_habits()
        updated = 0
        
        for habit in habits:
            new_confidence = habit["confidence"]
            
            # 已验证的习惯置信度提升到0.95
            if habit["is_verified"]:
                new_confidence = 0.95
            else:
                # 基于出现次数调整置信度
                occur_count = habit["occur_count"]
                if occur_count >= 10:
                    new_confidence = min(new_confidence + 0.2, 0.9)
                elif occur_count >= 5:
                    new_confidence = min(new_confidence + 0.1, 0.8)
            
            # 有冲突的习惯置信度降低
            if habit.get("has_conflict", False):
                new_confidence = max(new_confidence - 0.3, 0.1)
            
            if abs(new_confidence - habit["confidence"]) > 0.01:
                # 更新置信度
                # 这里需要扩展sqlite_store的update_habit方法，暂时先返回计数
                updated += 1
        
        return updated
    
    def extract_temporal_patterns(self) -> List[Dict]:
        """深度挖掘时序模式，识别复杂的周期性习惯"""
        memories = self.memory_system.search_memory("", limit=500)
        pattern_counts = defaultdict(int)
        pattern_details = defaultdict(list)
        
        for mem in memories:
            content = mem.get("content", "")
            created_at = mem.get("created_at")
            if not created_at:
                continue
                
            try:
                event_time = datetime.fromisoformat(created_at)
            except:
                continue
            
            # 识别各种时间模式
            for pattern in self.TIME_PATTERNS:
                matches = re.finditer(pattern, content)
                for match in matches:
                    pattern_str = match.group()
                    pattern_counts[pattern_str] += 1
                    pattern_details[pattern_str].append({
                        "time": event_time,
                        "content": content[:100]
                    })
        
        # 只保留出现至少3次的模式
        temporal_habits = []
        for pattern, count in pattern_counts.items():
            if count >= 3:
                # 推断习惯内容
                example = pattern_details[pattern][0]["content"]
                habit_content = f"周期性习惯：{pattern} {example}"
                
                temporal_habits.append({
                    "pattern": pattern,
                    "occur_count": count,
                    "content": habit_content,
                    "first_occur": min(p["time"] for p in pattern_details[pattern]).isoformat(),
                    "last_occur": max(p["time"] for p in pattern_details[pattern]).isoformat()
                })
        
        return temporal_habits
    
    def get_user_habits(self, category: str = None, min_confidence: float = 0.6, 
                        min_occur_count: int = 3, only_verified: bool = False,
                        include_conflicts: bool = False) -> Dict:
        """获取识别到的用户习惯，包含冲突检测结果"""
        habits = self.store.get_habits(
            category=category,
            min_confidence=min_confidence,
            min_occur_count=min_occur_count,
            only_verified=only_verified
        )
        
        result = {
            "habits": habits,
            "total": len(habits)
        }
        
        if include_conflicts:
            result["conflicts"] = self.detect_conflicting_habits()
        
        return result

# 全局实例
_habit_extractor_instance: Optional[HabitExtractor] = None

def get_habit_extractor() -> HabitExtractor:
    """获取全局习惯提取器实例"""
    global _habit_extractor_instance
    if _habit_extractor_instance is None:
        _habit_extractor_instance = HabitExtractor()
    return _habit_extractor_instance
