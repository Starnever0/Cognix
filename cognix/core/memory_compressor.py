from typing import List, Dict, Optional
import re
from cognix.core.memory_system import get_memory_system

class MemoryCompressor:
    """
    记忆压缩流水线
    负责从会话内容中提取高价值信息，分类写入长期记忆
    避免记忆污染，保证长期记忆的质量
    """
    
    def __init__(self, memory_system = None):
        self.memory_system = memory_system or get_memory_system()
        
        # 分类关键词映射
        self.category_keywords = {
            "user": [
                "我是", "姓名", "名字", "职位", "角色", "工作", "岗位",
                "常用语言", "语言", "说", "沟通", "风格", "我的", "我习惯",
                "我叫", "称呼", "职位是", "从事", "负责"
            ],
            "settings": [
                "默认", "设置", "偏好", "喜欢", "总是", "永远", "格式",
                "视图", "通知", "静音", "模板", "输出", "展示", "显示",
                "用什么格式", "用什么模式"
            ],
            "office": [
                "周报", "会议", "开会", "发送给", "发给", "抄送", "收件人",
                "每周", "每月", "每天", "定期", "流程", "习惯", "工作流",
                "报销", "审批", "待办", "任务", "日程", "日历", "提醒",
                "几点", "之前", "之后", "固定", "惯例"
            ],
            "feedback": [
                "以后", "应该", "需要", "要", "不要", "别", "建议", "最好",
                "应该要", "应该是", "不对", "错了", "纠正", "修正", "问题",
                "下次", "注意", "改", "调整", "改进", "回答", "回复"
            ],
            "reference": [
                "地址", "链接", "网址", "文档", "规范", "手册", "指南",
                "仓库", "git", "项目地址", "联系方式", "电话", "邮箱",
                "密码", "密钥", "配置", "参数", "参考", "资料"
            ]
        }
        
        # 触发阈值
        self.round_threshold = 20  # 会话轮数阈值
        self.token_threshold = 0.8  # Token阈值（占上下文窗口的比例）
        self.default_token_limit = 8000  # 默认上下文窗口大小
    
    def should_compress(self, 
                       round_count: int, 
                       token_count: int, 
                       task_finished: bool = False, 
                       user_request: bool = False,
                       token_limit: Optional[int] = None) -> bool:
        """
        判断是否需要进行记忆压缩
        :param round_count: 当前会话轮数
        :param token_count: 当前已使用的Token数量
        :param task_finished: 任务是否完成
        :param user_request: 用户是否主动要求保存
        :param token_limit: 上下文Token上限，默认使用default_token_limit
        :return: 是否需要压缩
        """
        token_limit = token_limit or self.default_token_limit
        
        if user_request:
            return True
        
        if task_finished:
            return True
        
        if round_count >= self.round_threshold:
            return True
        
        if token_count >= token_limit * self.token_threshold:
            return True
        
        return False
    
    def _classify_content(self, content: str) -> str:
        """
        根据内容自动分类到对应的记忆分类
        :param content: 记忆内容
        :return: 分类名称：user/settings/office/feedback/reference
        """
        content_lower = content.lower()
        
        # 计算每个分类的匹配得分
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in content_lower:
                    score += 1
            scores[category] = score
        
        # 返回得分最高的分类
        max_score = max(scores.values())
        if max_score == 0:
            return "reference"  # 默认分类到reference
        
        # 找到第一个得分最高的分类
        for category, score in scores.items():
            if score == max_score:
                return category
        
        return "reference"
    
    def _extract_key_information(self, content: str) -> str:
        """
        从会话内容中提取关键信息，去除冗余
        :param content: 原始会话内容
        :return: 提取后的关键信息
        """
        # 移除多余的空白和换行
        content = re.sub(r'\s+', ' ', content).strip()
        
        # 移除AI的回复内容，只保留用户的关键指令
        lines = content.split("用户：")
        user_contents = []
        for line in lines[1:]:  # 跳过第一个空元素
            if "AI：" in line:
                user_part = line.split("AI：")[0].strip()
                if user_part:
                    user_contents.append(user_part)
            else:
                if line.strip():
                    user_contents.append(line.strip())
        
        if user_contents:
            extracted = "\n".join(f"- {content}" for content in user_contents if len(content) > 5)
            return extracted
        
        # 如果没有明确的用户对话标记，返回简化后的内容
        return content
    
    def compress_session(self, session_content: str) -> List[Dict]:
        """
        压缩会话内容，提取高价值记忆并分类
        :param session_content: 完整会话内容
        :return: 提取到的记忆列表，每个包含category, heading, content
        """
        key_info = self._extract_key_information(session_content)
        if not key_info:
            return []
        
        # 按行拆分，逐行分类
        memories = []
        lines = key_info.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # 去除前导的"- "标记
            if line.startswith("- "):
                line = line[2:].strip()
            
            category = self._classify_content(line)
            
            # 生成标题：取前20个字符作为标题
            heading = line[:20] + "..." if len(line) > 20 else line
            
            memories.append({
                "category": category,
                "heading": heading,
                "content": line
            })
        
        return memories
    
    def compress_and_save(self, session_content: str, auto_save: bool = True) -> List[Dict]:
        """
        压缩会话并自动保存到对应的长期记忆
        :param session_content: 完整会话内容
        :param auto_save: 是否自动保存到记忆系统
        :return: 提取到的记忆列表
        """
        memories = self.compress_session(session_content)
        
        if auto_save and memories:
            for mem in memories:
                try:
                    self.memory_system.add_classified_memory(
                        category=mem["category"],
                        heading=mem["heading"],
                        content=mem["content"]
                    )
                except Exception:
                    # 保存失败时忽略，不影响整体流程
                    pass
        
        return memories
    
    def process_event(self, event: "Event") -> None:
        """
        处理事件总线的事件，用于自动触发记忆压缩
        :param event: 事件对象
        """
        # 目前只处理会话结束事件
        if event.event_type == "session_end":
            session_content = event.metadata.get("session_content", "")
            if session_content:
                self.compress_and_save(session_content)


# 全局实例
_compressor_instance: Optional[MemoryCompressor] = None

def get_memory_compressor() -> MemoryCompressor:
    """获取全局记忆压缩器实例"""
    global _compressor_instance
    if _compressor_instance is None:
        _compressor_instance = MemoryCompressor()
    return _compressor_instance
