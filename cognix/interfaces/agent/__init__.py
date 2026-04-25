from typing import Dict, List, Optional, Any, Union
from datetime import datetime


class AgentMemoryInterface:
    def __init__(self, memory_system=None):
        if memory_system is None:
            from cognix.core.memory_system import memory_system as default_memory
            self.memory = default_memory
        else:
            self.memory = memory_system

    def add_memory(self, 
                  memory_type: str, 
                  key: str, 
                  value: Any, 
                  session_id: str = None,
                  confidence: float = 1.0) -> int:
        if session_id:
            return self.memory.add_short_term_memory(session_id, key, value)
        return self.memory.add_long_term_memory(memory_type, key, value, confidence)

    def get_memory(self, 
                  key: str, 
                  session_id: str = None) -> Union[Dict, None]:
        if session_id:
            return self.memory.get_short_term_memory(session_id, key)
        return self.memory.get_long_term_memory(key=key)

    def search_memories(self, 
                       query: str, 
                       memory_type: str = None, 
                       limit: int = 10) -> List[Dict]:
        return self.memory.search_memories(query, memory_type, limit)

    def delete_memory(self, 
                     key: str, 
                     session_id: str = None) -> bool:
        if session_id:
            self.memory.delete_short_term_memory(session_id, key)
            return True
        return self.memory.delete_long_term_memory(key)

    def prepare_context(self, 
                       session_id: str, 
                       query: str = None) -> Dict:
        return self.memory.prepare_context_for_agent(session_id, query)

    def record_interaction(self, 
                          session_id: str, 
                          user_input: str, 
                          agent_response: str, 
                          tool_calls: List[Dict] = None):
        return self.memory.record_agent_interaction(session_id, user_input, agent_response, tool_calls)

    def list_memories(self, memory_type: str = None) -> List[Dict]:
        return self.memory.get_long_term_memory(memory_type)

    def update_memory(self, 
                     key: str, 
                     value: Any = None, 
                     confidence: float = None):
        self.memory.update_long_term_memory(key, value, confidence)

    def add_memory_link(self, 
                       source_key: str, 
                       target_key: str, 
                       relation_type: str = "related_to", 
                       confidence: float = 0.8):
        self.memory.add_memory_link(source_key, target_key, relation_type, confidence)

    def get_related_memories(self, 
                            key: str, 
                            relation_type: str = None) -> List[Dict]:
        return self.memory.get_related_memories(key, relation_type)

    def import_memories(self, memories: List[Dict]):
        self.memory.import_memories(memories)

    def export_memories(self, memory_type: str = None) -> List[Dict]:
        return self.memory.export_memories(memory_type)


agent_memory_interface = AgentMemoryInterface()


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

    def remember(self, key: str, value: Any, memory_type: str = "fact", confidence: float = 1.0) -> MemoryQueryResponse:
        try:
            memory_id = self.interface.add_memory(memory_type, key, value, confidence=confidence)
            return MemoryQueryResponse(True, {"memory_id": memory_id}, "记忆添加成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"添加失败: {str(e)}")

    def recall(self, key: str = None, query: str = None, memory_type: str = None) -> MemoryQueryResponse:
        try:
            if key:
                result = self.interface.get_memory(key)
            elif query and memory_type:
                result = self.interface.search_memories(query, memory_type)
            elif query:
                result = self.interface.search_memories(query)
            elif memory_type:
                result = self.interface.list_memories(memory_type)
            else:
                result = self.interface.list_memories()
            return MemoryQueryResponse(True, result, "查询成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"查询失败: {str(e)}")

    def forget(self, key: str) -> MemoryQueryResponse:
        try:
            success = self.interface.delete_memory(key)
            return MemoryQueryResponse(success, None, "删除成功" if success else "记忆不存在")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"删除失败: {str(e)}")

    def contextualize(self, session_id: str, query: str = None) -> MemoryQueryResponse:
        try:
            context = self.interface.prepare_context(session_id, query)
            return MemoryQueryResponse(True, context, "上下文获取成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"获取失败: {str(e)}")

    def learn(self, session_id: str, user_input: str, agent_response: str, tool_calls: List[Dict] = None) -> MemoryQueryResponse:
        try:
            interaction_id = self.interface.record_interaction(session_id, user_input, agent_response, tool_calls)
            return MemoryQueryResponse(True, {"interaction_id": interaction_id}, "学习成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"学习失败: {str(e)}")

    def connect(self, key1: str, key2: str, relation: str = "related_to") -> MemoryQueryResponse:
        try:
            self.interface.add_memory_link(key1, key2, relation)
            return MemoryQueryResponse(True, None, "关联建立成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"建立关联失败: {str(e)}")

    def get_connections(self, key: str, relation_type: str = None) -> MemoryQueryResponse:
        try:
            connections = self.interface.get_related_memories(key, relation_type)
            return MemoryQueryResponse(True, connections, "查询成功")
        except Exception as e:
            return MemoryQueryResponse(False, None, f"查询失败: {str(e)}")