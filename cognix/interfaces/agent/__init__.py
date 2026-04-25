from typing import Dict, List, Optional, Any
from datetime import datetime


class AgentMemoryInterface:
    def __init__(self, memory_system=None):
        if memory_system is None:
            from cognix.core.memory_system import get_memory_system
            self.memory = get_memory_system()
        else:
            self.memory = memory_system
    
    def add_memory(self, 
                  heading: str, 
                  content: str, 
                  date: datetime = None,
                  persistent: bool = False) -> bool:
        """添加记忆
        
        Args:
            heading: 记忆标题
            content: 记忆内容
            date: 记忆日期（默认为今天）
            persistent: 是否添加到持久记忆（MEMORY.md）
        """
        try:
            if persistent:
                self.memory.add_persistent_memory(heading, content)
            else:
                self.memory.add_memory(heading, content, date)
            return True
        except Exception:
            return False
    
    def search(self, 
              query: str, 
              limit: int = 10,
              source: str = None) -> List[Dict]:
        """搜索记忆
        
        Args:
            query: 搜索关键词
            limit: 返回结果数
            source: 来源（memory/persistent）
        """
        return self.memory.search_memory(query, limit, source)
    
    def get_context(self, 
                   days_back: int = 1,
                   session_id: str = None) -> str:
        """获取上下文
        
        Args:
            days_back: 回溯天数
            session_id: 会话ID（用于短期记忆）
        """
        context = self.memory.get_daily_context(days_back)
        
        if session_id:
            short_term = self.memory.get_short_term(session_id)
            if short_term:
                short_term_text = "\n## 短期记忆\n"
                for item in short_term:
                    short_term_text += f"- {item['key']}: {item['value']}\n"
                context += short_term_text
        
        return context
    
    def add_short_term(self, 
                      session_id: str, 
                      key: str, 
                      value: Any):
        """添加短期记忆"""
        self.memory.add_short_term(session_id, key, value)
    
    def get_short_term(self, 
                      session_id: str) -> List[Dict]:
        """获取短期记忆"""
        return self.memory.get_short_term(session_id)
    
    def clear_short_term(self, session_id: str):
        """清除短期记忆"""
        self.memory.clear_short_term(session_id)
    
    def read_file(self, 
                 file_path: str, 
                 start_line: int = None, 
                 end_line: int = None) -> str:
        """读取记忆文件"""
        from pathlib import Path
        return self.memory.read_memory_file(Path(file_path), start_line, end_line)
    
    def rebuild_index(self):
        """重建索引"""
        self.memory.rebuild_index()


# 延迟创建，避免导入时就初始化
agent_memory_interface = None


class MemoryQueryResponse:
    def __init__(self, success: bool, data: Any = None, message: str = ""):
        self.success = success
        self.data = data
        self.message = message
    
    def to_dict(self):
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message
        }


class AgentMemoryClient:
    def __init__(self, agent_id: str = None, memory_system=None):
        self.agent_id = agent_id
        self.interface = AgentMemoryInterface(memory_system)
    
    def remember(self, 
                heading: str, 
                content: str, 
                persistent: bool = False) -> MemoryQueryResponse:
        """记住新内容
        
        Args:
            heading: 记忆标题
            content: 记忆内容
            persistent: 是否持久化
        """
        try:
            success = self.interface.add_memory(heading, content, persistent=persistent)
            return MemoryQueryResponse(success, None, "记忆添加成功" if success else "添加失败")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"添加失败: {str(e)}")
    
    def recall(self, 
              query: str = None, 
              source: str = None, 
              limit: int = 10) -> MemoryQueryResponse:
        """回忆记忆
        
        Args:
            query: 搜索关键词（如果为空则返回上下文）
            source: 来源
            limit: 返回数量
        """
        try:
            if query:
                result = self.interface.search(query, limit, source)
                return MemoryQueryResponse(True, result, "查询成功")
            else:
                context = self.interface.get_context(days_back=limit)
                return MemoryQueryResponse(True, {"context": context}, "上下文获取成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"查询失败: {str(e)}")
    
    def contextualize(self, 
                     session_id: str = None, 
                     days_back: int = 1) -> MemoryQueryResponse:
        """获取上下文"""
        try:
            context = self.interface.get_context(days_back, session_id)
            return MemoryQueryResponse(True, {"context": context}, "上下文获取成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"获取失败: {str(e)}")
    
    def note_short_term(self, 
                       session_id: str, 
                       key: str, 
                       value: Any) -> MemoryQueryResponse:
        """记录短期记忆"""
        try:
            self.interface.add_short_term(session_id, key, value)
            return MemoryQueryResponse(True, None, "短期记忆记录成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"记录失败: {str(e)}")
    
    def get_short_term(self, session_id: str) -> MemoryQueryResponse:
        """获取短期记忆"""
        try:
            result = self.interface.get_short_term(session_id)
            return MemoryQueryResponse(True, result, "获取成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"获取失败: {str(e)}")
    
    def clear_session(self, session_id: str) -> MemoryQueryResponse:
        """清除会话短期记忆"""
        try:
            self.interface.clear_short_term(session_id)
            return MemoryQueryResponse(True, None, "清除成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"清除失败: {str(e)}")
    
    def rebuild_index(self) -> MemoryQueryResponse:
        """重建索引"""
        try:
            self.interface.rebuild_index()
            return MemoryQueryResponse(True, None, "索引重建成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"重建失败: {str(e)}")
