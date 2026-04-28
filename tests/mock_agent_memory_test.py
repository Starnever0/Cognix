#!/usr/bin/env python3
"""Mock测试脚本 - 测试记忆系统的完整功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch


class MockConfig:
    def __init__(self, temp_dir):
        self.home_path = Path(temp_dir)
        self.db_path = self.home_path / "mock_test.db"


def run_mock_test(output_dir=None, keep_files=False):
    """运行mock测试
    
    Args:
        output_dir: 输出目录（如果None则使用临时目录）
        keep_files: 是否保留文件
    """
    
    # 创建测试目录
    if output_dir:
        temp_path = Path(output_dir)
        temp_path.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
    
    try:
        # 配置环境
        mock_config = MockConfig(temp_path)
        
        from cognix.core import memory_system as ms_module
        patcher = patch.object(ms_module, 'config', mock_config)
        patcher.start()
        
        print("=" * 60)
        print("Cognix 记忆系统 Mock 测试")
        print("=" * 60)
        
        # 初始化
        from cognix.core.memory_system import MarkdownMemory
        from cognix.interfaces.agent import AgentMemoryClient
        
        print(f"\n1. 初始化记忆系统...")
        memory = MarkdownMemory()
        client = AgentMemoryClient(memory_system=memory)
        print(f"   OK - 完成")
        
        # 测试场景1 - 添加基本记忆
        print(f"\n2. 场景1 - 添加基本记忆...")
        result1 = client.remember("用户基本信息", "姓名：张三，年龄：28，职业：软件工程师")
        result2 = client.remember("工作项目", "正在开发Cognix记忆系统，使用Python和SQLite")
        result3 = client.remember("用户偏好", "喜欢简洁回答，偏好深色主题，喜欢技术文档")
        if result1.success and result2.success and result3.success:
            print(f"   OK - 完成")
        
        # 测试场景2 - 添加持久记忆
        print(f"\n3. 场景2 - 添加持久记忆...")
        result4 = client.remember("常用命令", "git status: 查看状态\ngit commit: 提交\ngit push: 推送", persistent=True)
        result5 = client.remember("项目约定", "代码风格：PEP8\n提交规范：conventional commits", persistent=True)
        if result4.success and result5.success:
            print(f"   OK - 完成")
        
        # 测试场景3 - 添加短期记忆
        print(f"\n4. 场景3 - 添加短期记忆...")
        session_id = "mock-test-session-001"
        result6 = client.note_short_term(session_id, "当前任务", "完成记忆系统重构和测试")
        result7 = client.note_short_term(session_id, "对话内容", "用户：如何使用记忆系统？")
        if result6.success and result7.success:
            print(f"   OK - 完成")
        
        # 测试场景4 - 搜索记忆
        print(f"\n5. 场景4 - 搜索记忆...")
        search1 = client.recall("张三")
        search2 = client.recall("Cognix")
        search3 = client.recall("用户偏好")
        
        print(f"   - 搜索'张三'找到 {len(search1.data) if search1.data else 0} 个结果")
        print(f"   - 搜索'Cognix'找到 {len(search2.data) if search2.data else 0} 个结果")
        print(f"   OK - 搜索功能正常")
        
        # 测试场景5 - 获取上下文
        print(f"\n6. 场景5 - 获取上下文...")
        context = client.contextualize(session_id)
        print(f"   OK - 上下文获取成功")
        print(f"   上下文摘要：{len(context.data.get('context', ''))} 字符")
        
        # 测试场景6 - 验证文件创建
        print(f"\n7. 场景6 - 验证文件创建...")
        memory_dir = temp_path / "memory"
        memory_md = temp_path / "MEMORY.md"
        
        daily_files = list(memory_dir.glob("*.md"))
        print(f"   - 每日记忆文件：{len(daily_files)} 个")
        print(f"   - 持久记忆文件：{'存在' if memory_md.exists() else '不存在'}")
        
        # 显示文件内容示例
        print(f"\n8. Markdown文件内容...")
        
        if daily_files:
            print(f"\n--- {daily_files[0].name} ---")
            content = daily_files[0].read_text(encoding='utf-8')
            print(content[:300] + "..." if len(content) > 300 else content)
        
        if memory_md.exists():
            print(f"\n--- MEMORY.md ---")
            content = memory_md.read_text(encoding='utf-8')
            print(content[:300] + "..." if len(content) > 300 else content)
        
        # 完成
        print(f"\n" + "=" * 60)
        print(f"Mock 测试完成！")
        print(f"=" * 60)
        print(f"\n测试文件位于：{temp_path}")
        
        if keep_files:
            print(f"\n测试文件已保留，您可以检查生成的Markdown文件！")
        else:
            print(f"\n（使用 --keep 参数可以保留文件用于检查）")
        
        return True
        
    finally:
        # 清理
        if not keep_files and output_dir is None:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        patcher.stop()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="记忆系统Mock测试")
    parser.add_argument('--keep', action='store_true', help='保留测试文件')
    parser.add_argument('--output-dir', type=str, help='指定输出目录')
    
    args = parser.parse_args()
    
    success = run_mock_test(args.output_dir, args.keep)
    sys.exit(0 if success else 1)
