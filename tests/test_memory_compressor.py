from datetime import datetime
from unittest.mock import Mock
from cognix.core.memory_compressor import MemoryCompressor
from cognix.core.event_bus import Event

def test_memory_classification():
    """测试记忆内容自动分类"""
    mock_memory = Mock()
    compressor = MemoryCompressor(memory_system=mock_memory)
    
    # 测试user分类
    content = "我是张三，在公司担任产品经理职位，平时喜欢用中文沟通，输出喜欢简洁明了的风格"
    category = compressor._classify_content(content)
    assert category == "user"
    
    # 测试settings分类
    content = "以后输出默认都用Markdown格式，表格视图用列表模式，通知默认静音"
    category = compressor._classify_content(content)
    assert category == "settings"
    
    # 测试office分类
    content = "以后周报默认发给李总和王经理，每周五下午5点之前发，开会前5分钟提醒我准备材料"
    category = compressor._classify_content(content)
    assert category == "office"
    
    # 测试feedback分类
    content = "以后回答问题先给结论，少用表格，语气更简洁一点，多给可执行的建议"
    category = compressor._classify_content(content)
    assert category == "feedback"
    
    # 测试reference分类
    content = "项目仓库地址是git@github.com:example/cognix.git，团队规范文档在飞书文档里"
    category = compressor._classify_content(content)
    assert category == "reference"

def test_extract_key_information():
    """测试提取关键信息"""
    mock_memory = Mock()
    compressor = MemoryCompressor(memory_system=mock_memory)
    
    content = """用户说：
以后周报默认发给李总和王经理，每周五下午5点之前发送，
内容要包含本周进展、遇到的blocker和下周计划，
格式用Markdown，不要太啰嗦。
"""
    extracted = compressor._extract_key_information(content)
    
    assert "周报默认发给李总和王经理" in extracted
    assert "每周五下午5点之前发送" in extracted
    assert "内容要包含本周进展、遇到的blocker和下周计划" in extracted
    assert "格式用Markdown" in extracted

def test_should_compress():
    """测试压缩触发条件判断"""
    mock_memory = Mock()
    compressor = MemoryCompressor(memory_system=mock_memory)
    
    # 轮数达到阈值
    assert compressor.should_compress(round_count=20, token_count=1000, task_finished=False, user_request=False) == True
    
    # Token达到阈值
    assert compressor.should_compress(round_count=10, token_count=7500, task_finished=False, user_request=False) == True
    
    # 任务完成
    assert compressor.should_compress(round_count=5, token_count=1000, task_finished=True, user_request=False) == True
    
    # 用户主动要求
    assert compressor.should_compress(round_count=3, token_count=500, task_finished=False, user_request=True) == True
    
    # 都不满足
    assert compressor.should_compress(round_count=5, token_count=1000, task_finished=False, user_request=False) == False

def test_compress_session():
    """测试完整的会话压缩流程"""
    mock_memory = Mock()
    compressor = MemoryCompressor(memory_system=mock_memory)
    
    session_content = """
    用户：你好，我是张三，产品经理
    AI：您好张三，有什么可以帮您的？
    用户：以后我发周报默认要发给李总和王经理，每周五下午5点前发
    AI：好的，我记住了，以后您的周报默认收件人是李总和王经理，周五下午5点前发送。
    用户：对了，以后回答我问题先给结论，少用表格
    AI：明白了，以后我会先给结论，尽量少用表格展示内容。
    """
    
    result = compressor.compress_session(session_content)
    
    assert len(result) > 0
    # 应该至少分到两个分类
    categories = set(item['category'] for item in result)
    assert "user" in categories
    assert "office" in categories
    assert "feedback" in categories
