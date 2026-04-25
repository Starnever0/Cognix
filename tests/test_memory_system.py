import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import sqlite3

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from cognix.utils.config import config


class TestMemorySystem:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp(dir='d:/Mycode/LLM/Cognix')
        self.original_db_path = config.db_path
        self.original_home_path = config.home_path
        
        config.home_path = Path(self.temp_dir)
        config.db_path = config.home_path / "cognix.db"
        
        from cognix.core.memory_system import MemorySystem
        self.memory_system = MemorySystem()
        
        from cognix.interfaces.agent import AgentMemoryClient
        self.agent_client = AgentMemoryClient(memory_system=self.memory_system)

    def teardown_method(self):
        self.memory_system.close()
        config.db_path = self.original_db_path
        config.home_path = self.original_home_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_get_short_term_memory(self):
        session_id = "test_session_001"
        key = "user_name"
        value = {"name": "张三"}

        memory_id = self.memory_system.add_short_term_memory(session_id, key, value)
        assert memory_id > 0

        result = self.memory_system.get_short_term_memory(session_id, key)
        assert result is not None
        assert result["key"] == key
        assert result["value"] == value

    def test_add_and_get_long_term_memory(self):
        key = "test_fact_key"
        value = {"content": "测试事实内容"}

        memory_id = self.memory_system.add_long_term_memory("fact", key, value)
        assert memory_id > 0

        result = self.memory_system.get_long_term_memory(key=key)
        assert result is not None
        assert result["key"] == key
        assert result["value"] == value
        assert result["memory_type"] == "fact"

    def test_long_term_memory_md_file_created(self):
        key = "test_md_key"
        value = {"content": "测试MD文件内容"}

        memory_id = self.memory_system.add_long_term_memory("preference", key, value)
        result = self.memory_system.get_long_term_memory(key=key)

        assert result["md_file_path"] is not None
        assert Path(result["md_file_path"]).exists()

    def test_search_memories(self):
        self.memory_system.add_long_term_memory("fact", "user_zhangsan", {"name": "张三", "department": "研发部"})
        self.memory_system.add_long_term_memory("fact", "user_lisi", {"name": "李四", "department": "产品部"})
        self.memory_system.add_long_term_memory("preference", "report_format", {"value": "table"})

        results = self.memory_system.search_memories("张三")
        assert len(results) >= 1
        assert any(r["key"] == "user_zhangsan" for r in results)

        results = self.memory_system.search_memories("report", memory_type="preference")
        assert len(results) >= 1
        assert any(r["key"] == "report_format" for r in results)

    def test_memory_confidence_decay(self):
        key = "test_decay_key"
        self.memory_system.add_long_term_memory("fact", key, {"content": "测试衰减"}, confidence=1.0)

        result = self.memory_system.get_long_term_memory(key=key)
        assert result["confidence"] == 1.0

        cursor = self.memory_system._conn.cursor()
        cursor.execute('UPDATE long_term_memory SET accessed_at = ? WHERE key = ?', 
                      ((datetime.now() - timedelta(days=31)).isoformat(), key))
        self.memory_system._conn.commit()

        self.memory_system.decay_memory_confidence(days_threshold=30, decay_rate=0.1)
        result = self.memory_system.get_long_term_memory(key=key)
        assert result["confidence"] <= 0.9

    def test_add_memory_link(self):
        self.memory_system.add_long_term_memory("fact", "memory_a", {"content": "A"})
        self.memory_system.add_long_term_memory("fact", "memory_b", {"content": "B"})

        self.memory_system.add_memory_link("memory_a", "memory_b", "related_to", 0.8)

        related = self.memory_system.get_related_memories("memory_a")
        assert len(related) >= 1
        assert any(r["key"] == "memory_b" for r in related)

    def test_prepare_context_for_agent(self):
        session_id = "test_session_002"
        self.memory_system.add_short_term_memory(session_id, "context_key", {"value": "test"})
        self.memory_system.add_long_term_memory("fact", "user_info", {"name": "测试用户"})
        self.memory_system.add_long_term_memory("preference", "output_format", {"value": "markdown"})
        self.memory_system.add_long_term_memory("experience", "task_pattern", {"pattern": "weekly"})

        context = self.memory_system.prepare_context_for_agent(session_id, "测试用户")

        assert "short_term" in context
        assert "long_term" in context
        assert len(context["short_term"]) > 0
        assert len(context["long_term"]["facts"]) > 0

    def test_record_agent_interaction(self):
        session_id = "test_session_003"
        interaction_id = self.memory_system.record_agent_interaction(
            session_id,
            "用户输入",
            "Agent响应",
            [{"tool": "search", "args": {"query": "test"}}]
        )

        assert interaction_id > 0
        memories = self.memory_system.get_short_term_memory(session_id)
        assert len(memories) > 0


class TestAgentMemoryClient:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp(dir='d:/Mycode/LLM/Cognix')
        self.original_db_path = config.db_path
        self.original_home_path = config.home_path
        
        config.home_path = Path(self.temp_dir)
        config.db_path = config.home_path / "cognix.db"
        
        from cognix.core.memory_system import MemorySystem
        self.memory_system = MemorySystem()
        
        from cognix.interfaces.agent import AgentMemoryClient
        self.client = AgentMemoryClient(memory_system=self.memory_system)

    def teardown_method(self):
        self.memory_system.close()
        config.db_path = self.original_db_path
        config.home_path = self.original_home_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_remember_and_recall(self):
        result = self.client.remember("client_test_key", {"data": "test"}, "fact")
        assert result.success
        assert "memory_id" in result.data

        result = self.client.recall(key="client_test_key")
        assert result.success
        assert result.data is not None
        assert result.data["key"] == "client_test_key"

    def test_forget(self):
        self.client.remember("forget_test_key", {"data": "to forget"}, "fact")
        result = self.client.forget("forget_test_key")
        assert result.success

        result = self.client.forget("non_existent_key")
        assert result.message != "删除成功"

    def test_contextualize(self):
        result = self.client.contextualize("test_session", "测试查询")
        assert result.success
        assert "short_term" in result.data
        assert "long_term" in result.data

    def test_connect_and_get_connections(self):
        self.client.remember("connect_a", {"content": "A"}, "fact")
        self.client.remember("connect_b", {"content": "B"}, "fact")

        result = self.client.connect("connect_a", "connect_b", "related_to")
        assert result.success

        result = self.client.get_connections("connect_a")
        assert result.success
        assert len(result.data) >= 1

    def test_search_with_query(self):
        self.client.remember("search_test_1", {"name": "测试数据1"}, "fact")
        self.client.remember("search_test_2", {"name": "测试数据2"}, "fact")

        result = self.client.recall(query="测试")
        assert result.success
        assert len(result.data) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])