#!/usr/bin/env python3
"""调试索引问题"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockConfig:
    def __init__(self, temp_dir):
        self.home_path = Path(temp_dir)
        self.db_path = self.home_path / "debug.db"


def debug_index():
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    print(f"测试目录：{temp_path}")
    
    mock_config = MockConfig(temp_path)
    
    from cognix.core import memory_system as ms_module
    patcher = patch.object(ms_module, 'config', mock_config)
    patcher.start()
    
    try:
        from cognix.core.memory_system import MarkdownMemory
        
        memory = MarkdownMemory()
        
        # 添加测试记忆
        print("\n1. 添加记忆...")
        memory.add_memory("测试", "这是测试内容，包含张三和Cognix")
        
        # 检查文件
        print("\n2. 检查文件...")
        md_files = list(memory.memory_dir.glob("*.md"))
        print(f"  找到 {len(md_files)} 个Markdown文件")
        for f in md_files:
            print(f"  - {f.name}")
            print(f"    内容：{f.read_text(encoding='utf-8')[:200]}")
        
        # 检查数据库
        print("\n3. 检查数据库...")
        cursor = memory._conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM files")
        print(f"  files表记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT path, hash FROM files")
        for row in cursor.fetchall():
            print(f"  - 文件：{row[0]}")
            print(f"    哈希：{row[1][:20]}...")
        
        cursor.execute("SELECT COUNT(*) FROM chunks")
        print(f"  chunks表记录数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT id, start_line, end_line, SUBSTR(text, 1, 50) FROM chunks")
        for row in cursor.fetchall():
            print(f"  - 块ID：{row[0]}")
            print(f"    行：{row[1]}-{row[2]}")
            print(f"    文本：{row[3]}")
        
        # 测试搜索
        print("\n4. 测试搜索...")
        results = memory.search_memory("张三")
        print(f"  搜索'张三'结果数：{len(results)}")
        for r in results:
            print(f"  - {r['path']}")
            print(f"    分数：{r['score']}")
            print(f"    内容：{r['text'][:100]}")
        
        # 测试直接读取搜索
        print("\n5. 直接读取Markdown搜索...")
        for md_file in memory.memory_dir.glob("*.md"):
            content = md_file.read_text(encoding='utf-8')
            if '张三' in content:
                print(f"  ✓ 在 {md_file.name} 中找到'张三'")
                print(f"    完整内容：{content}")
        
        print("\n调试完成！")
        
    finally:
        patcher.stop()
        import shutil
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    debug_index()
