from typing import List, Dict, Optional
from cognix.core.memory_system import get_memory_system

class RetrievalEngine:
    """
    双轨检索引擎
    实现"固定注入 + 动态召回"双机制，提升AI助手理解能力
    
    固定核心记忆注入：每次任务默认注入user/settings/office核心记忆
    动态相关记忆召回：FTS5检索feedback/reference/sessions/skills相关内容
    """
    
    def __init__(self, memory_system = None):
        self.memory_system = memory_system or get_memory_system()
        self.default_limit = 5  # 默认召回数量
    
    def get_fixed_memory_injection(self) -> str:
        """
        获取固定核心记忆注入内容
        包含：user.md摘要、settings.md、office.md高频规则
        """
        parts = []
        
        # 用户记忆
        try:
            user_memory = self.memory_system.classifier.get_memory("user")
            if user_memory and len(user_memory) > 10:
                parts.append(f"## 用户记忆\n{user_memory}")
        except Exception:
            pass
        
        # 设置记忆
        try:
            settings_memory = self.memory_system.classifier.get_memory("settings")
            if settings_memory and len(settings_memory) > 10:
                parts.append(f"## 设置记忆\n{settings_memory}")
        except Exception:
            pass
        
        # 办公习惯
        try:
            office_memory = self.memory_system.classifier.get_memory("office")
            if office_memory and len(office_memory) > 10:
                parts.append(f"## 办公习惯\n{office_memory}")
        except Exception:
            pass
        
        return "\n\n".join(parts)
    
    def dynamic_retrieval(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """
        动态相关记忆召回
        使用SQLite FTS5进行全文检索
        
        :param query: 查询关键词
        :param limit: 返回数量限制，默认使用default_limit
        :return: 检索结果列表
        """
        limit = limit or self.default_limit
        
        try:
            results = self.memory_system.search_memory(query, limit=limit)
            return results[:limit]
        except Exception:
            return []
    
    def build_context(self, query: str, dynamic_limit: Optional[int] = None) -> str:
        """
        构建完整的上下文，包含固定记忆和动态召回记忆
        
        :param query: 用户查询
        :param dynamic_limit: 动态召回数量限制
        :return: 完整的上下文字符串
        """
        parts = []
        
        # 添加固定核心记忆
        fixed_memory = self.get_fixed_memory_injection()
        if fixed_memory:
            parts.append(f"【核心记忆】\n{fixed_memory}")
        
        # 添加动态相关记忆
        dynamic_results = self.dynamic_retrieval(query, limit=dynamic_limit)
        if dynamic_results:
            dynamic_texts = []
            for i, result in enumerate(dynamic_results, 1):
                text = result.get("text", "")
                if text:
                    # 限制每个结果的长度
                    if len(text) > 200:
                        text = text[:200] + "..."
                    dynamic_texts.append(f"{i}. {text}")
            
            if dynamic_texts:
                parts.append(f"\n【相关记忆】\n{chr(10).join(dynamic_texts)}")
        else:
            parts.append("\n【相关记忆】\n暂无相关记忆")
        
        return "\n".join(parts)
    
    def enhance_prompt(self, original_prompt: str, query: str = "") -> str:
        """
        增强原始prompt，注入记忆上下文
        
        :param original_prompt: 原始prompt
        :param query: 用户查询（用于动态检索）
        :return: 增强后的prompt
        """
        context = self.build_context(query)
        
        if context:
            enhanced_prompt = f"""
以下是关于用户的记忆信息，请参考这些信息来回答问题：

{context}

---

{original_prompt}
"""
            return enhanced_prompt.strip()
        
        return original_prompt


# 全局实例
_retrieval_engine_instance: Optional[RetrievalEngine] = None

def get_retrieval_engine() -> RetrievalEngine:
    """获取全局检索引擎实例"""
    global _retrieval_engine_instance
    if _retrieval_engine_instance is None:
        _retrieval_engine_instance = RetrievalEngine()
    return _retrieval_engine_instance
