import json
import redis
from typing import Dict, Any, Optional, List
from cognix.utils.config import config

class RedisShortTermMemory:
    """
    Redis短期记忆存储
    支持自动过期、JSON序列化，Redis不可用时自动回退到内存模式
    """
    def __init__(self, 
                 host: str = None, 
                 port: int = None, 
                 db: int = None, 
                 password: str = None,
                 ttl: int = None,
                 fallback_to_memory: bool = True):
        self.host = host or config.redis_host
        self.port = port or config.redis_port
        self.db = db or config.redis_db
        self.password = password or config.redis_password
        self.ttl = ttl or config.short_term_ttl
        self.fallback_to_memory = fallback_to_memory
        
        self._redis_client: Optional[redis.Redis] = None
        self._memory_fallback: Dict[str, Dict[str, Any]] = {}
        self._use_memory_fallback = False
        
        self._init_redis()
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            self._redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 测试连接
            self._redis_client.ping()
            self._use_memory_fallback = False
        except redis.ConnectionError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True
            else:
                raise
    
    def _get_key_prefix(self, session_id: str) -> str:
        """获取Redis键前缀"""
        return f"stm:{session_id}"
    
    def add(self, session_id: str, key: str, value: Any) -> None:
        """
        添加短期记忆
        :param session_id: 会话ID
        :param key: 记忆键
        :param value: 记忆值（支持JSON可序列化类型）
        """
        if self._use_memory_fallback:
            if session_id not in self._memory_fallback:
                self._memory_fallback[session_id] = {}
            self._memory_fallback[session_id][key] = value
            return
        
        try:
            redis_key = self._get_key_prefix(session_id)
            value_json = json.dumps(value, ensure_ascii=False)
            self._redis_client.hset(redis_key, key, value_json)
            self._redis_client.expire(redis_key, self.ttl)
        except redis.RedisError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True
                self.add(session_id, key, value)
    
    def get(self, session_id: str, key: str, default: Any = None) -> Optional[Any]:
        """
        获取短期记忆
        :param session_id: 会话ID
        :param key: 记忆键
        :param default: 不存在时返回的默认值
        :return: 记忆值
        """
        if self._use_memory_fallback:
            return self._memory_fallback.get(session_id, {}).get(key, default)
        
        try:
            redis_key = self._get_key_prefix(session_id)
            value_json = self._redis_client.hget(redis_key, key)
            if value_json is None:
                return default
            return json.loads(value_json)
        except redis.RedisError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True
                return self.get(session_id, key, default)
            return default
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        获取整个会话的所有记忆
        :param session_id: 会话ID
        :return: 会话记忆字典
        """
        if self._use_memory_fallback:
            return self._memory_fallback.get(session_id, {}).copy()
        
        try:
            redis_key = self._get_key_prefix(session_id)
            all_items = self._redis_client.hgetall(redis_key)
            result = {}
            for key, value_json in all_items.items():
                try:
                    result[key] = json.loads(value_json)
                except json.JSONDecodeError:
                    result[key] = value_json
            return result
        except redis.RedisError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True
                return self.get_session(session_id)
            return {}
    
    def delete(self, session_id: str, key: str) -> bool:
        """
        删除会话中的某个记忆
        :param session_id: 会话ID
        :param key: 要删除的键
        :return: 是否删除成功
        """
        if self._use_memory_fallback:
            if session_id in self._memory_fallback and key in self._memory_fallback[session_id]:
                del self._memory_fallback[session_id][key]
                return True
            return False
        
        try:
            redis_key = self._get_key_prefix(session_id)
            deleted = self._redis_client.hdel(redis_key, key)
            return deleted > 0
        except redis.RedisError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True
                return self.delete(session_id, key)
            return False
    
    def clear_session(self, session_id: str) -> None:
        """
        清除整个会话的记忆
        :param session_id: 会话ID
        """
        if self._use_memory_fallback:
            if session_id in self._memory_fallback:
                del self._memory_fallback[session_id]
            return
        
        try:
            redis_key = self._get_key_prefix(session_id)
            self._redis_client.delete(redis_key)
        except redis.RedisError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True
                self.clear_session(session_id)
    
    def list_sessions(self) -> List[str]:
        """
        列出所有活跃会话ID
        :return: 会话ID列表
        """
        if self._use_memory_fallback:
            return list(self._memory_fallback.keys())
        
        try:
            keys = self._redis_client.keys(f"{self._get_key_prefix('*')}")
            session_ids = [key.split(":", 2)[1] for key in keys]
            return session_ids
        except redis.RedisError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True
                return self.list_sessions()
            return []
    
    def update_ttl(self, session_id: str, ttl: Optional[int] = None) -> None:
        """
        更新会话的过期时间
        :param session_id: 会话ID
        :param ttl: 新的过期时间（秒），默认使用全局ttl
        """
        if self._use_memory_fallback:
            # 内存模式下不支持TTL
            return
        
        try:
            ttl = ttl or self.ttl
            redis_key = self._get_key_prefix(session_id)
            self._redis_client.expire(redis_key, ttl)
        except redis.RedisError:
            if self.fallback_to_memory:
                self._use_memory_fallback = True


# 全局实例
_short_term_instance: Optional[RedisShortTermMemory] = None

def get_short_term_memory() -> RedisShortTermMemory:
    """获取全局短期记忆实例"""
    global _short_term_instance
    if _short_term_instance is None:
        _short_term_instance = RedisShortTermMemory()
    return _short_term_instance
