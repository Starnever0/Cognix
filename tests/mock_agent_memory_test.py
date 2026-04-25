#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock Agent Memory System Test Script
模拟Agent与记忆系统的完整交互场景

用法:
    python mock_agent_memory_test.py [--keep] [--output-dir DIR]
    
参数:
    --keep          测试完成后保留测试文件，不立即清理
    --output-dir    指定输出目录（默认自动创建临时目录）
"""

import sys
import argparse
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from cognix.utils.config import config


def parse_args():
    parser = argparse.ArgumentParser(description="Mock Agent Memory System Test")
    parser.add_argument('--keep', action='store_true', 
                        help='测试完成后保留测试文件，不立即清理')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='指定输出目录（默认自动创建临时目录）')
    return parser.parse_args()


args = parse_args()

# 设置输出目录
if args.output_dir:
    temp_dir = args.output_dir
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
else:
    temp_dir = tempfile.mkdtemp(dir='d:/Mycode/LLM/Cognix')

original_db_path = config.db_path
original_home_path = config.home_path

config.home_path = Path(temp_dir)
config.db_path = config.home_path / "cognix.db"
config.home_path.mkdir(parents=True, exist_ok=True)

from cognix.core.memory_system import MemorySystem
from cognix.interfaces.agent import AgentMemoryClient


def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_step(step: str):
    print(f"\n-> {step}")


def print_result(result):
    if hasattr(result, 'success'):
        status = "[OK] 成功" if result.success else "[FAIL] 失败"
        print(f"  状态: {status}")
        if result.message:
            print(f"  消息: {result.message}")
        if result.data:
            print(f"  数据: {result.data}")
    else:
        print(f"  结果: {result}")


class MockAgentMemoryTest:
    def __init__(self, keep_files=False):
        global temp_dir, original_db_path, original_home_path
        self.temp_dir = temp_dir
        self.original_db_path = original_db_path
        self.original_home_path = original_home_path
        self.keep_files = keep_files
        
        self.memory_system = MemorySystem()
        self.agent_client = AgentMemoryClient(agent_id="mock_agent_001", memory_system=self.memory_system)
        
        print("="*60)
        print("  Mock Agent 记忆系统测试")
        print("="*60)
        print(f"  测试环境: {self.temp_dir}")
        print(f"  Agent ID: mock_agent_001")
        if self.keep_files:
            print(f"  保留文件: 是")
        print("="*60)
        
    def cleanup(self):
        self.memory_system.close()
        global config
        config.db_path = self.original_db_path
        config.home_path = self.original_home_path
        
        if self.keep_files:
            print(f"\n[提示] 测试文件已保留在: {self.temp_dir}")
            print(f"[提示] 使用清理脚本或手动删除该目录")
        else:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("\n[OK] 清理完成")
        
    def run_full_scenario(self):
        try:
            print_separator("场景1: 初始化用户信息")
            self.test_initialize_user_info()
            
            print_separator("场景2: 记录用户偏好")
            self.test_record_user_preferences()
            
            print_separator("场景3: 记录用户交互")
            self.test_record_user_interaction()
            
            print_separator("场景4: 关联相关记忆")
            self.test_connect_memories()
            
            print_separator("场景5: 为Agent准备上下文")
            self.test_prepare_agent_context()
            
            print_separator("场景6: 搜索相关记忆")
            self.test_search_memories()
            
            print_separator("场景7: 遗忘某些记忆")
            self.test_forget_memories()
            
            print_separator("场景8: 上下文总结")
            self.test_context_summary()
            
            print("\n" + "="*60)
            print("  *** 所有测试场景执行完成！ ***")
            print("="*60)
            
        except Exception as e:
            print(f"\n[ERROR] 测试出错: {e}")
            import traceback
            traceback.print_exc()
    
    def test_initialize_user_info(self):
        print_step("添加用户基本信息到长期记忆")
        
        result = self.agent_client.remember(
            "user_name", 
            {"name": "张三", "age": 28, "role": "软件工程师"},
            "fact"
        )
        print_result(result)
        
        result = self.agent_client.remember(
            "user_workplace",
            {"company": "科技公司", "department": "人工智能部", "position": "高级工程师"},
            "fact"
        )
        print_result(result)
        
        result = self.agent_client.remember(
            "user_contact",
            {"email": "zhangsan@example.com", "phone": "138****8888"},
            "fact"
        )
        print_result(result)
        
        print_step("验证记忆是否存储成功")
        result = self.agent_client.recall(key="user_name")
        print_result(result)
        
    def test_record_user_preferences(self):
        print_step("记录用户偏好设置")
        
        result = self.agent_client.remember(
            "theme_preference",
            {"value": "dark", "description": "深色主题"},
            "preference"
        )
        print_result(result)
        
        result = self.agent_client.remember(
            "language",
            {"value": "zh-CN", "description": "中文"},
            "preference"
        )
        print_result(result)
        
        result = self.agent_client.remember(
            "response_style",
            {"value": "concise", "description": "简洁风格"},
            "preference"
        )
        print_result(result)
        
        result = self.agent_client.remember(
            "coding_language",
            {"value": "Python", "description": "喜欢的编程语言"},
            "preference"
        )
        print_result(result)
        
    def test_record_user_interaction(self):
        print_step("添加短期记忆（会话级别）")
        
        session_id = "session_2024_04_25_001"
        
        self.memory_system.add_short_term_memory(
            session_id,
            "last_query",
            {"query": "如何优化Python代码性能", "timestamp": "2024-04-25 10:30:00"}
        )
        print("[OK] 添加短期记忆: last_query")
        
        self.memory_system.add_short_term_memory(
            session_id,
            "current_task",
            {"task": "代码优化咨询", "status": "in_progress"}
        )
        print("[OK] 添加短期记忆: current_task")
        
        self.memory_system.record_agent_interaction(
            session_id,
            "如何优化Python代码性能？",
            "可以通过以下方式优化...",
            [{"tool": "code_analysis", "args": {"language": "Python"}}]
        )
        print("[OK] 记录Agent交互记录")
        
    def test_connect_memories(self):
        print_step("添加工作项目信息")
        
        self.agent_client.remember(
            "project_alpha",
            {"name": "Alpha项目", "description": "AI助手开发", "status": "进行中"},
            "fact"
        )
        
        self.agent_client.remember(
            "project_beta",
            {"name": "Beta项目", "description": "数据分析平台", "status": "已完成"},
            "fact"
        )
        
        print_step("关联记忆")
        result = self.agent_client.connect(
            "user_name",
            "project_alpha",
            "related_to"
        )
        print_result(result)
        
        result = self.agent_client.connect(
            "project_alpha",
            "coding_language",
            "derived_from"
        )
        print_result(result)
        
        print_step("获取关联记忆")
        result = self.agent_client.get_connections("user_name")
        print_result(result)
        
    def test_prepare_agent_context(self):
        print_step("为Agent准备上下文")
        
        session_id = "session_2024_04_25_001"
        
        result = self.agent_client.contextualize(
            session_id,
            "请帮我优化Python代码"
        )
        print_result(result)
        
        if result.success and result.data:
            print(f"\n  短期记忆: {len(result.data.get('short_term', []))} 条")
            print(f"  长期事实: {len(result.data.get('long_term', {}).get('facts', []))} 条")
            print(f"  偏好设置: {len(result.data.get('long_term', {}).get('preferences', []))} 条")
            print(f"  经验记录: {len(result.data.get('long_term', {}).get('experiences', []))} 条")
    
    def test_search_memories(self):
        print_step("搜索包含'项目'的记忆")
        result = self.agent_client.recall(query="项目")
        print_result(result)
        
        print_step("搜索包含'Python'的记忆")
        result = self.agent_client.recall(query="Python")
        print_result(result)
        
        print_step("搜索偏好类型的记忆")
        result = self.agent_client.recall(memory_type="preference")
        print_result(result)
        
    def test_forget_memories(self):
        print_step("添加临时记忆")
        self.agent_client.remember(
            "temp_data",
            {"content": "这是临时数据，即将删除"},
            "fact"
        )
        
        print_step("删除临时记忆")
        result = self.agent_client.forget("temp_data")
        print_result(result)
        
        print_step("验证是否还能获取已删除的记忆")
        result = self.agent_client.recall(key="temp_data")
        print_result(result)
        
    def test_context_summary(self):
        print_step("查看所有长期记忆")
        
        cursor = self.memory_system._conn.cursor()
        cursor.execute('SELECT key, memory_type, confidence FROM long_term_memory')
        memories = cursor.fetchall()
        
        print(f"\n  长期记忆统计:")
        for key, mem_type, conf in memories:
            print(f"    - {key} ({mem_type}) [置信度: {conf:.2f}]")
        
        print_step("查看Markdown文件存储")
        md_path = config.home_path / "memories"
        if md_path.exists():
            md_files = list(md_path.glob("*.md"))
            print(f"\n  Markdown文件: {len(md_files)} 个")
            for f in md_files[:3]:
                print(f"    - {f.name}")


def main():
    test = MockAgentMemoryTest(keep_files=args.keep)
    try:
        test.run_full_scenario()
    finally:
        test.cleanup()


if __name__ == "__main__":
    main()
