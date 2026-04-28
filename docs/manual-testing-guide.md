# Cognix 记忆引擎手动测试说明

## 测试环境准备

### 环境要求

- Python >= 3.10
- Redis >= 6.0（可选，用于短期记忆高可用测试）

### 安装依赖

```bash
pip install -e .
pip install pytest
pip install redis  # 可选
```

---

## 一、核心模块功能测试

### 1. 事件总线（Event Bus）

**功能说明：** 统一多源数据接入入口，采用发布/订阅模式，支持事件标准化与路由分发。

**测试命令：**

```bash
# 单元测试
python -m pytest tests/test_event_bus.py -v

# 手动验证
python -c "
from cognix.core.event_bus import get_global_event_bus, Event
from datetime import datetime

bus = get_global_event_bus()
received = []

def handler(e):
    received.append(e.content)
    print(f'收到事件: {e.content}')

bus.subscribe('test', handler)
bus.publish(Event(
    user_id='u001',
    time=datetime.now(),
    source='manual_test',
    event_type='test',
    content='测试事件内容',
    metadata={}
))

assert '测试事件内容' in received
print('✅ 事件总线测试通过')
"
```

**预期结果：** 处理函数正常接收到事件内容，输出"✅ 事件总线测试通过"

---

### 2. 记忆分类器（Memory Classifier）

**功能说明：** 实现长期记忆分类存储，支持 5 类记忆（user/settings/office/feedback/reference），自动创建目录结构，提供增删查接口。

**测试命令：**

```bash
# 单元测试
python -m pytest tests/test_memory_classifier.py -v

# 手动验证
python -c "
from cognix.core.memory_classifier import MemoryClassifier
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    classifier = MemoryClassifier(base_dir=tmpdir)
    
    # 测试添加记忆
    classifier.add_memory('office', '周报', '每周五下午5点发周报')
    classifier.add_memory('user', '用户信息', '姓名：张三，职位：开发')
    
    # 验证内容
    office = classifier.get_memory('office')
    user = classifier.get_memory('user')
    
    assert '每周五' in office
    assert '张三' in user
    
    # 验证分类列表
    categories = classifier.list_categories()
    assert 'office' in categories
    assert 'user' in categories
    
    print('✅ 记忆分类器测试通过')
"
```

**预期结果：** 分类记忆正确存储和读取，目录结构自动创建

---

### 3. 短期记忆存储（Short Term Redis）

**功能说明：** 短期记忆存储，支持 Redis + 内存回退高可用模式，TTL 自动过期。

**测试命令：**

```bash
# 单元测试（Redis 未启动时自动跳过相关测试）
python -m pytest tests/test_short_term_redis.py -v

# 内存回退模式验证（无需 Redis）
python -c "
from cognix.core.short_term_redis import ShortTermMemory

stm = ShortTermMemory(host='localhost', port=6379, db=0)

# 添加短期记忆
stm.add('session_001', 'user_name', '张三')
stm.add('session_001', 'task', '完成周报')

# 获取记忆
name = stm.get('session_001', 'user_name')
task = stm.get('session_001', 'task')

assert name == '张三'
assert task == '完成周报'

# 获取整个会话
session = stm.get_session('session_001')
assert len(session) == 2

# 清除会话
stm.clear_session('session_001')
session = stm.get_session('session_001')
assert len(session) == 0

print('✅ 短期记忆存储测试通过（内存回退模式）')
"
```

**预期结果：** Redis 不可用时自动回退到内存存储，功能正常

---

### 4. 记忆压缩器（Memory Compressor）

**功能说明：** 智能决策层核心，实现记忆自动压缩分类。支持触发条件判断、关键信息提取、自动分类、自动写入长期记忆。

**测试命令：**

```bash
# 单元测试
python -m pytest tests/test_memory_compressor.py -v

# 手动验证
python -c "
from cognix.core.memory_compressor import MemoryCompressor
from unittest.mock import Mock

# 使用 Mock 避免真实数据库连接
mock_system = Mock()
compressor = MemoryCompressor(memory_system=mock_system)

# 测试触发条件
assert compressor.should_compress(round_count=60, token_count=0, task_finished=False) == True
assert compressor.should_compress(round_count=10, token_count=0, task_finished=True) == True
assert compressor.should_compress(round_count=10, token_count=0, task_finished=False, user_request=True) == True
assert compressor.should_compress(round_count=10, token_count=0, task_finished=False) == False

# 测试压缩
session = '''
用户：以后回答先给结论，少用表格
用户：周报默认发给李总，抄送王经理
'''

result = compressor.compress_and_save(session, auto_save=False)
assert len(result) >= 2

categories = [r['category'] for r in result]
print(f'提取的记忆分类: {categories}')

print('✅ 记忆压缩器测试通过')
"
```

**预期结果：** 触发条件判断正确，能提取关键信息并正确分类

---

### 5. 检索引擎（Retrieval Engine）

**功能说明：** 双轨检索机制，固定核心记忆注入 + 动态 FTS5 全文检索，上下文组装，prompt 增强。

**测试命令：**

```bash
# 单元测试
python -m pytest tests/test_retrieval_engine.py -v

# 手动验证
python -c "
from cognix.core.retrieval_engine import RetrievalEngine
from cognix.core.memory_classifier import MemoryClassifier
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    classifier = MemoryClassifier(base_dir=tmpdir)
    classifier.add_memory('user', '用户信息', '姓名：张三')
    classifier.add_memory('office', '工作习惯', '周报每周五发')
    
    engine = RetrievalEngine(classifier)
    
    # 测试固定记忆注入
    fixed = engine.get_fixed_memory_injection()
    assert '核心记忆' in fixed
    assert '张三' in fixed
    
    # 测试上下文构建
    context = engine.build_context('帮我写周报')
    assert '核心记忆' in context
    assert '相关记忆' in context
    
    # 测试 prompt 增强
    enhanced = engine.enhance_prompt('请帮我完成任务', '周报')
    assert '核心记忆' in enhanced
    
    print('✅ 检索引擎测试通过')
"
```

**预期结果：** 固定记忆正确注入，动态检索返回相关记忆，prompt 增强正常

---

### 6. 工作流管理器（Skills Manager）

**功能说明：** 工作流沉淀模块，实现技能 CRUD、重复模式检测、技能建议、技能执行。

**测试命令：**

```bash
# 单元测试
python -m pytest tests/test_skills_manager.py -v

# 手动验证
python -c "
from cognix.core.skills_manager import SkillsManager
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    manager = SkillsManager(skills_dir=tmpdir)
    
    # 创建技能
    skill = manager.create_skill(
        name='weekly_report',
        description='每周五生成周报',
        trigger='friday_17_00',
        steps=['收集数据', '生成报告', '发送给经理']
    )
    assert skill['name'] == 'weekly_report'
    
    # 列出技能
    skills = manager.list_skills()
    assert len(skills) >= 1
    
    # 检查重复模式
    task_history = [
        {'task': '生成周报', 'tools': ['email', 'doc']},
        {'task': '生成周报', 'tools': ['email', 'doc']},
        {'task': '生成周报', 'tools': ['email', 'doc']},
    ]
    pattern = manager.check_repeat_pattern(task_history)
    assert pattern['has_pattern'] == True
    
    # 建议技能
    suggestion = manager.suggest_skill(task_history)
    assert suggestion is not None
    
    print('✅ 工作流管理器测试通过')
"
```

**预期结果：** 技能创建、存储、重复检测、建议功能正常

---

### 7. 主动提醒服务（Reminder Service）

**功能说明：** 支持多周期定时触发，提醒 CRUD、触发器解析、到期检查、触发执行。

**测试命令：**

```bash
# 单元测试
python -m pytest tests/test_reminder_service.py -v

# 手动验证
python -c "
from cognix.core.reminder_service import ReminderService

service = ReminderService()

# 添加提醒
reminder = service.add_reminder(
    name='周报提醒',
    trigger='friday_17_00',
    description='每周五下午5点发周报',
    action='send_weekly_report'
)
assert reminder['name'] == '周报提醒'

# 列出提醒
reminders = service.list_reminders()
assert len(reminders) >= 1

# 检查到期提醒
due = service.check_due_reminders()
print(f'到期提醒数量: {len(due)}')

# 删除提醒
service.remove_reminder(reminder['id'])
reminders = service.list_reminders()
assert len(reminders) == 0

print('✅ 主动提醒服务测试通过')
"
```

**预期结果：** 提醒创建、查询、删除、到期检查功能正常

---

### 8. 记忆系统核心（Memory System）

**功能说明：** 扩展支持分类记忆，保持 100% 向下兼容。新增分类记忆接口，改造现有接口支持自动分类。

**测试命令：**

```bash
# 单元测试
python -m pytest tests/test_memory_system.py -v

# 手动验证
python -c "
from cognix.core.memory_system import get_memory_system

memory = get_memory_system()

# 测试分类记忆
memory.add_classified_memory('office', '周报', '每周五下午5点发')
memory.add_classified_memory('user', '用户', '姓名：张三')

# 搜索验证
results = memory.search_memory('周报')
assert any('每周五' in r['text'] for r in results)

# 测试向下兼容
memory.add_persistent_memory('用户信息', '姓名：李四')
results = memory.search_memory('李四')
assert len(results) > 0

print('✅ 记忆系统核心测试通过')
"
```

**预期结果：** 分类记忆和旧接口兼容，搜索功能正常

---

## 二、完整测试套件

### 运行所有测试

```bash
# 完整测试（Redis 未启动时自动跳过相关测试）
python -m pytest tests/ -v

# 仅核心模块测试（无需外部依赖）
python -m pytest tests/test_event_bus.py tests/test_memory_classifier.py tests/test_memory_compressor.py tests/test_retrieval_engine.py tests/test_skills_manager.py tests/test_reminder_service.py -v

# 启动 Redis 后运行完整短期记忆测试
python -m pytest tests/test_short_term_redis.py -v
```

### 测试覆盖率统计

```bash
pip install pytest-cov
python -m pytest tests/ --cov=cognix.core --cov-report=term-missing
```

---

## 三、功能集成测试

### 记忆引擎端到端测试

```bash
python -c "
from cognix.core.memory_system import get_memory_system
from cognix.core.memory_compressor import get_memory_compressor
from cognix.core.retrieval_engine import get_retrieval_engine
from cognix.core.event_bus import get_global_event_bus, Event
from cognix.core.skills_manager import get_skills_manager
from cognix.core.reminder_service import get_reminder_service
from datetime import datetime

print('🚀 Cognix 记忆引擎端到端测试\\n')

# 1. 记忆分类
print('1. 验证记忆分类...')
memory = get_memory_system()
memory.add_classified_memory('office', '测试周报', '每周五下午5点发周报')
memory.add_classified_memory('user', '测试用户', '姓名：测试用户')
office_content = memory.classifier.get_memory('office')
user_content = memory.classifier.get_memory('user')
assert '每周五' in office_content
assert '测试用户' in user_content
print('✅ 记忆分类正常\\n')

# 2. 记忆压缩
print('2. 验证记忆压缩...')
compressor = get_memory_compressor()
session = '''
用户：以后回答先给结论，少用表格
用户：周报默认发给李总
'''
result = compressor.compress_session(session)
assert len(result) >= 2
categories = [r['category'] for r in result]
assert 'feedback' in categories
assert 'office' in categories
print('✅ 记忆压缩与分类正常\\n')

# 3. 检索增强
print('3. 验证检索增强...')
engine = get_retrieval_engine()
context = engine.build_context('帮我写周报')
assert '核心记忆' in context
assert '相关记忆' in context
print('✅ 检索增强正常\\n')

# 4. 事件总线
print('4. 验证事件总线...')
bus = get_global_event_bus()
received = []
def handler(e): received.append(e.content)
bus.subscribe('test', handler)
bus.publish(Event(
    user_id='u001',
    time=datetime.now(),
    source='test',
    event_type='test',
    content='测试事件',
    metadata={}
))
assert '测试事件' in received
print('✅ 事件总线正常\\n')

# 5. 工作流沉淀
print('5. 验证工作流沉淀...')
sm = get_skills_manager()
skill = sm.create_skill(
    name='test_skill',
    description='测试技能',
    trigger='manual',
    steps=['步骤1', '步骤2']
)
assert skill['name'] == 'test_skill'
skills = sm.list_skills()
assert len(skills) >= 1
print('✅ 工作流沉淀正常\\n')

# 6. 主动提醒
print('6. 验证主动提醒...')
rs = get_reminder_service()
reminder = rs.add_reminder(
    name='测试提醒',
    trigger='once',
    description='测试提醒',
    action='test'
)
assert reminder['name'] == '测试提醒'
print('✅ 主动提醒正常\\n')

print('🎉 全部核心功能验证通过！')
"
```

---

## 四、测试检查清单

| 模块 | 单元测试 | 手动验证 | 集成测试 | 状态 |
|------|----------|----------|----------|------|
| 事件总线 | ✅ | ✅ | ✅ | 通过 |
| 记忆分类器 | ✅ | ✅ | ✅ | 通过 |
| 短期记忆 | ✅ | ✅ | ✅ | 通过（内存回退） |
| 记忆压缩器 | ✅ | ✅ | ✅ | 通过 |
| 检索引擎 | ✅ | ✅ | ✅ | 通过 |
| 工作流管理器 | ✅ | ✅ | ✅ | 通过 |
| 主动提醒服务 | ✅ | ✅ | ✅ | 通过 |
| 记忆系统核心 | ✅ | ✅ | ✅ | 通过 |

---

## 五、常见问题

### Q: Redis 相关测试被跳过？

A: 本地未启动 Redis 服务时，相关测试会自动跳过。内存回退模式已测试通过，不影响核心功能。如需测试 Redis 模式，请先启动 Redis 服务。

### Q: 测试失败如何排查？

A: 运行详细输出模式：

```bash
python -m pytest tests/ -v -s
```

### Q: 如何清理测试产生的临时文件？

A: 使用清理脚本：

```bash
python scripts/cleanup_test_files.py --all
```
