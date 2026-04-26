from unittest.mock import Mock, MagicMock
from cognix.core.retrieval_engine import RetrievalEngine

def test_get_fixed_memory_injection():
    """测试固定核心记忆注入"""
    mock_memory = Mock()
    mock_memory.classifier = Mock()
    
    mock_memory.classifier.get_memory = Mock(side_effect=[
        "# User 记忆\n\n## 基本信息\n姓名：张三，职位：产品经理",
        "# Settings 记忆\n\n## 输出格式\n默认输出Markdown格式",
        "# Office 记忆\n\n## 周报习惯\n每周五下午5点发送周报给李总"
    ])
    
    engine = RetrievalEngine(memory_system=mock_memory)
    
    fixed_memory = engine.get_fixed_memory_injection()
    
    assert "张三" in fixed_memory
    assert "产品经理" in fixed_memory
    assert "默认输出Markdown格式" in fixed_memory
    assert "每周五下午5点发送周报" in fixed_memory
    assert "李总" in fixed_memory

def test_dynamic_retrieval():
    """测试动态相关记忆召回"""
    mock_memory = Mock()
    mock_memory.search_memory = Mock(return_value=[
        {"text": "用户反馈：回答先给结论", "source": "memory"},
        {"text": "项目仓库地址：git@github.com:example/cognix", "source": "memory"},
        {"text": "历史对话：讨论周报格式", "source": "memory"}
    ])
    
    engine = RetrievalEngine(memory_system=mock_memory)
    
    results = engine.dynamic_retrieval("周报")
    
    assert len(results) == 3
    assert any("回答先给结论" in r['text'] for r in results)
    assert any("项目仓库地址" in r['text'] for r in results)
    assert any("周报格式" in r['text'] for r in results)

def test_build_context():
    """测试构建完整上下文"""
    mock_memory = Mock()
    mock_memory.classifier = Mock()
    mock_memory.search_memory = Mock(return_value=[
        {"text": "用户反馈：少用表格", "source": "memory"}
    ])
    
    mock_memory.classifier.get_memory = Mock(side_effect=[
        "# User 记忆\n\n## 基本信息\n姓名：张三",
        "# Settings 记忆\n\n## 通知设置\n默认静音",
        "# Office 记忆\n\n## 会议习惯\n开会前准备材料"
    ])
    
    engine = RetrievalEngine(memory_system=mock_memory)
    
    context = engine.build_context("帮我写周报")
    
    assert "张三" in context
    assert "默认静音" in context
    assert "开会前准备材料" in context
    assert "少用表格" in context
    assert "用户记忆" in context
    assert "设置记忆" in context
    assert "办公习惯" in context
    assert "相关记忆" in context

def test_retrieval_limit():
    """测试检索数量限制"""
    mock_memory = Mock()
    mock_memory.search_memory = Mock(return_value=[
        {"text": "结果1", "source": "memory"},
        {"text": "结果2", "source": "memory"},
        {"text": "结果3", "source": "memory"},
        {"text": "结果4", "source": "memory"},
        {"text": "结果5", "source": "memory"},
        {"text": "结果6", "source": "memory"}  # 超过限制
    ])
    
    engine = RetrievalEngine(memory_system=mock_memory)
    
    results = engine.dynamic_retrieval("测试", limit=3)
    
    assert len(results) == 3

def test_empty_retrieval():
    """测试空检索结果"""
    mock_memory = Mock()
    mock_memory.search_memory = Mock(return_value=[])
    mock_memory.classifier = Mock()
    mock_memory.classifier.get_memory = Mock(return_value="# User 记忆\n\n")
    
    engine = RetrievalEngine(memory_system=mock_memory)
    
    context = engine.build_context("测试查询")
    
    assert "用户记忆" in context
    assert "相关记忆" in context
    # 没有相关记忆时应该有提示
    assert "暂无相关记忆" in context or len(context) > 0
