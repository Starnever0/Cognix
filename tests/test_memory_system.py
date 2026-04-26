#!/usr/bin/env python3
"""新的记忆系统测试用例 - Markdown + SQLite FTS5"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch


# 临时修改config.home_path和config.db_path
class MockConfig:
    def __init__(self, temp_dir):
        self.home_path = Path(temp_dir)
        self.db_path = self.home_path / "test.db"


class TestMarkdownMemory(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # 使用mock config
        self.mock_config = MockConfig(self.temp_path)
        
        # 导入并patch memory_system的config
        from cognix.core import memory_system as ms_module
        patcher = patch.object(ms_module, 'config', self.mock_config)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # 创建新的实例（避免单例污染）
        self.memory = ms_module.MarkdownMemory()
    
    def tearDown(self):
        """测试后清理"""
        self.memory.close()
        shutil.rmtree(self.temp_dir)
    
    def test_add_memory_and_index(self):
        """测试添加记忆并索引"""
        # 添加测试记忆
        self.memory.add_memory("事实记忆", "张三，28岁，软件工程师")
        self.memory.add_memory("用户偏好", "喜欢简洁回答，偏好深色主题")
        
        # 搜索测试
        results = self.memory.search_memory("张三")
        self.assertGreater(len(results), 0, "应该能找到记忆")
    
    def test_search_in_markdown(self):
        """测试Markdown内容搜索"""
        # 添加内容
        self.memory.add_memory("测试项目", "正在开发Cognix记忆系统")
        
        # 搜索
        results = self.memory.search_memory("Cognix")
        self.assertTrue(any("Cognix" in r['text'] for r in results))
    
    def test_daily_context(self):
        """测试获取每日上下文"""
        # 添加今天的记忆
        self.memory.add_memory("今天发生的事", "完成了记忆系统重构")
        
        # 获取上下文
        context = self.memory.get_daily_context(days_back=0)
        self.assertIn("记忆系统重构", context)
    
    def test_persistent_memory(self):
        """测试持久记忆"""
        # 添加持久记忆
        self.memory.add_persistent_memory("基本信息", "姓名：测试用户")
        
        # 搜索
        results = self.memory.search_memory("测试用户")
        self.assertTrue(any("测试用户" in r['text'] for r in results))
    
    def test_classified_memory_integration(self):
        """测试分类记忆集成"""
        # 测试分类记忆集成
        self.memory.add_classified_memory("office", "周报", "每周五发周报")
        
        # 搜索应该能找到分类记忆
        results = self.memory.search_memory("周报")
        assert any("每周五发周报" in r['text'] for r in results)
        
        # 现有add_persistent_memory应该兼容并自动分类
        self.memory.add_persistent_memory("用户信息", "姓名：张三，职位：开发工程师")
        results = self.memory.search_memory("张三")
        assert len(results) > 0
        
        # 测试自动分类到office（使用明确的办公关键词）
        self.memory.add_persistent_memory("会议安排", "每周一上午10点开例会")
        results = self.memory.search_memory("例会")
        assert len(results) > 0
        # 验证分类记忆被正确存储和检索
        office_content = self.memory.classifier.get_memory("office")
        assert "例会" in office_content
    
    def test_short_term_memory(self):
        """测试短期记忆"""
        session_id = "test-session-123"
        
        # 添加短期记忆
        self.memory.add_short_term(session_id, "当前对话", "正在测试记忆系统")
        
        # 获取短期记忆
        short_term = self.memory.get_short_term(session_id)
        self.assertEqual(len(short_term), 1)
        self.assertEqual(short_term[0]['key'], "当前对话")
        
        # 清除
        self.memory.clear_short_term(session_id)
        self.assertEqual(len(self.memory.get_short_term(session_id)), 0)
    
    def test_read_memory_file(self):
        """测试读取记忆文件"""
        self.memory.add_memory("测试文件", "这是测试内容")
        
        # 查找创建的文件
        memory_files = list(self.memory.memory_dir.glob("*.md"))
        self.assertTrue(len(memory_files) > 0, "应该有记忆文件")
        
        # 读取
        content = self.memory.read_memory_file(memory_files[0])
        self.assertIn("测试内容", content)
    
    def test_rebuild_index(self):
        """测试重建索引"""
        # 添加一些内容
        self.memory.add_memory("测试1", "内容1")
        self.memory.add_memory("测试2", "内容2")
        
        # 重建
        self.memory.rebuild_index()
        
        # 搜索测试
        results = self.memory.search_memory("内容1")
        self.assertTrue(len(results) > 0, "索引重建后应该能搜索")
    
    def test_multiple_headings(self):
        """测试同一文件中的多个标题"""
        self.memory.add_memory("标题A", "内容A1")
        self.memory.add_memory("标题A", "内容A2")  # 追加到同一标题
        self.memory.add_memory("标题B", "内容B1")
        
        # 应该能找到两个标题
        results_a = self.memory.search_memory("标题A")
        results_b = self.memory.search_memory("标题B")
        self.assertTrue(len(results_a) > 0 and len(results_b) > 0)


class TestAgentMemoryClient(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        self.mock_config = MockConfig(self.temp_path)
        
        from cognix.core import memory_system as ms_module
        patcher = patch.object(ms_module, 'config', self.mock_config)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        self.memory = ms_module.MarkdownMemory()
        
        from cognix.interfaces.agent import AgentMemoryClient
        self.client = AgentMemoryClient(memory_system=self.memory)
    
    def tearDown(self):
        """测试后清理"""
        self.memory.close()
        shutil.rmtree(self.temp_dir)
    
    def test_remember_and_recall(self):
        """测试记住和回忆"""
        # 记住
        result = self.client.remember("测试内容", "这是要记住的内容")
        self.assertTrue(result.success)
        
        # 回忆
        recall_result = self.client.recall("测试内容")
        self.assertTrue(recall_result.success)
        self.assertTrue(len(recall_result.data) > 0)
    
    def test_contextualize(self):
        """测试获取上下文"""
        session_id = "test-session"
        
        self.client.remember("上下文测试", "这是上下文内容")
        self.client.note_short_term(session_id, "session_key", "session_value")
        
        context_result = self.client.contextualize(session_id)
        self.assertTrue(context_result.success)
        self.assertIn("上下文测试", context_result.data['context'])
    
    def test_short_term_session(self):
        """测试短期会话"""
        session_id = "test-session-456"
        
        self.client.note_short_term(session_id, "状态", "正在进行")
        get_result = self.client.get_short_term(session_id)
        self.assertTrue(get_result.success)
        
        clear_result = self.client.clear_session(session_id)
        self.assertTrue(clear_result.success)


if __name__ == '__main__':
    unittest.main()
