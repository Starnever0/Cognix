import os
import tempfile
import pytest
from cognix.core.memory_classifier import MemoryClassifier

def test_classified_memory_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        classifier = MemoryClassifier(tmpdir)
        
        # 测试添加记忆
        classifier.add_memory("office", "周报设置", "周报默认收件人：李总、王经理")
        classifier.add_memory("user", "基本信息", "姓名：张三，职位：产品经理")
        
        # 测试读取记忆
        office_memories = classifier.get_memory("office")
        assert "周报默认收件人" in office_memories
        assert "李总、王经理" in office_memories
        
        user_memories = classifier.get_memory("user")
        assert "张三" in user_memories
        assert "产品经理" in user_memories
        
        # 测试列出分类
        categories = classifier.list_categories()
        assert set(categories) == {"user", "settings", "office", "feedback", "reference"}
        
        # 测试自动创建目录
        assert os.path.exists(os.path.join(tmpdir, "sessions"))
        assert os.path.exists(os.path.join(tmpdir, "skills"))
        
        # 测试无效分类报错
        with pytest.raises(ValueError):
            classifier.add_memory("invalid_category", "测试", "内容")
        
        with pytest.raises(ValueError):
            classifier.get_memory("invalid_category")

def test_memory_file_format():
    with tempfile.TemporaryDirectory() as tmpdir:
        classifier = MemoryClassifier(tmpdir)
        
        classifier.add_memory("settings", "输出格式", "默认输出Markdown格式")
        
        settings_file = os.path.join(tmpdir, "settings.md")
        content = open(settings_file, encoding="utf-8").read()
        
        assert "# Settings 记忆" in content
        assert "## 输出格式" in content
        assert "默认输出Markdown格式" in content
