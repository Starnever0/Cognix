import pytest
import time
import redis
from cognix.core.short_term_redis import RedisShortTermMemory
from cognix.utils.config import config

# 检查Redis是否可用
def is_redis_available():
    try:
        r = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            socket_connect_timeout=1,
            socket_timeout=1
        )
        r.ping()
        return True
    except:
        return False

redis_available = pytest.mark.skipif(not is_redis_available(), reason="Redis服务不可用")

@redis_available
def test_redis_short_term_basic_operations():
    """测试Redis短期记忆基本操作"""
    stm = RedisShortTermMemory()
    
    session_id = "test-session-123"
    
    # 添加记忆
    stm.add(session_id, "task", "完成记忆系统开发")
    stm.add(session_id, "current_step", 2)
    stm.add(session_id, "context", {"project": "Cognix", "version": "1.0"})
    
    # 获取单个key
    task = stm.get(session_id, "task")
    assert task == "完成记忆系统开发"
    
    # 获取整个会话
    session_data = stm.get_session(session_id)
    assert len(session_data) == 3
    assert session_data["current_step"] == 2
    assert session_data["context"]["project"] == "Cognix"
    
    # 更新value
    stm.add(session_id, "current_step", 3)
    assert stm.get(session_id, "current_step") == 3
    
    # 删除key
    stm.delete(session_id, "context")
    assert stm.get(session_id, "context") is None
    assert len(stm.get_session(session_id)) == 2
    
    # 清除会话
    stm.clear_session(session_id)
    assert stm.get_session(session_id) == {}

@redis_available
def test_redis_short_term_ttl():
    """测试短期记忆TTL过期"""
    stm = RedisShortTermMemory(ttl=1)  # 1秒过期
    
    session_id = "test-ttl-session"
    stm.add(session_id, "temp_data", "will_expire")
    
    assert stm.get(session_id, "temp_data") == "will_expire"
    
    # 等待过期
    time.sleep(1.5)
    
    assert stm.get(session_id, "temp_data") is None
    assert stm.get_session(session_id) == {}

def test_redis_short_term_fallback_to_memory():
    """测试Redis不可用时回退到内存模式"""
    # 用错误的配置触发回退
    stm = RedisShortTermMemory(host="invalid-host", port=1234, fallback_to_memory=True)
    
    session_id = "test-fallback"
    stm.add(session_id, "test_key", "fallback_value")
    
    assert stm.get(session_id, "test_key") == "fallback_value"
    assert stm._use_memory_fallback == True

@redis_available
def test_redis_short_term_list_sessions():
    """测试列出所有活跃会话"""
    stm = RedisShortTermMemory()
    
    # 先清除所有会话
    for sid in stm.list_sessions():
        stm.clear_session(sid)
    
    stm.add("session1", "key1", "value1")
    stm.add("session2", "key2", "value2")
    stm.add("session3", "key3", "value3")
    
    sessions = stm.list_sessions()
    assert len(sessions) == 3
    assert set(sessions) == {"session1", "session2", "session3"}
