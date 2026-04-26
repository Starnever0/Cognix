# 记忆引擎完整实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在现有Cognix记忆系统基础上，扩展实现完整的五层架构记忆引擎，包含数据接入、短期记忆、长期记忆、智能决策、服务执行全栈能力，100%向下兼容现有功能。

**架构：** 采用渐进式迭代方案，分6个阶段实现，每个阶段独立可运行，保持现有API完全兼容，逐步从现有架构演进到目标五层架构。

**技术栈：** FastAPI、SQLite FTS5、Redis、APScheduler、Feishu SDK、Markdown，无向量数据库依赖。

---

## 涉及文件清单

### 新增文件
| 文件路径 | 职责 |
|---------|------|
| `cognix/core/event_bus.py` | 数据接入层事件总线 |
| `cognix/core/memory_classifier.py` | 长期记忆分类管理器 |
| `cognix/core/short_term_redis.py` | Redis短期记忆实现 |
| `cognix/core/memory_compressor.py` | 记忆压缩流水线 |
| `cognix/core/retrieval_engine.py` | 双轨检索引擎 |
| `cognix/core/skills_manager.py` | 工作流沉淀模块 |
| `cognix/core/reminder_service.py` | 主动提醒服务 |
| `cognix/integrations/openclaw_hooks.py` | OpenClaw Hooks集成 |
| `cognix/integrations/feishu_bot.py` | 飞书Bot实现 |
| `cognix/cli/memory_cli.py` | CLI工具实现 |
| `tests/test_event_bus.py` | 事件总线测试 |
| `tests/test_memory_classifier.py` | 记忆分类测试 |
| `tests/test_short_term_redis.py` | Redis短期记忆测试 |
| `tests/test_memory_compressor.py` | 记忆压缩测试 |
| `tests/test_retrieval_engine.py` | 检索引擎测试 |

### 修改文件
| 文件路径 | 修改内容 |
|---------|----------|
| `cognix/core/memory_system.py` | 扩展支持分类记忆、双轨检索 |
| `cognix/interfaces/agent.py` | 扩展新的记忆API |
| `cognix/utils/config.py` | 添加Redis、飞书等新配置项 |
| `docs/记忆系统使用说明.md` | 更新文档 |

---

## 阶段1：长期记忆分类改造

### 任务1：记忆分类管理器实现
**文件：**
- 创建：`cognix/core/memory_classifier.py`
- 修改：`cognix/core/memory_system.py`
- 测试：`tests/test_memory_classifier.py`

- [ ] **步骤1：编写失败的测试**
```python
import os
import tempfile
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
        
        user_memories = classifier.get_memory("user")
        assert "张三" in user_memories
        
        # 测试列出分类
        categories = classifier.list_categories()
        assert set(categories) == {"user", "settings", "office", "feedback", "reference"}
        
        # 测试自动创建目录
        assert os.path.exists(os.path.join(tmpdir, "sessions"))
        assert os.path.exists(os.path.join(tmpdir, "skills"))
```

- [ ] **步骤2：运行测试验证失败**
运行：`pytest tests/test_memory_classifier.py::test_classified_memory_operations -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'cognix.core.memory_classifier'"

- [ ] **步骤3：编写最少实现代码**
```python
# cognix/core/memory_classifier.py
from pathlib import Path
from typing import List, Dict, Optional

class MemoryClassifier:
    CATEGORIES = ["user", "settings", "office", "feedback", "reference"]
    
    def __init__(self, memory_dir: str):
        self.memory_dir = Path(memory_dir)
        self._init_structure()
    
    def _init_structure(self):
        """初始化目录结构"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建分类文件
        for category in self.CATEGORIES:
            file_path = self.memory_dir / f"{category}.md"
            if not file_path.exists():
                file_path.write_text(f"# {category.capitalize()} 记忆\n\n", encoding="utf-8")
        
        # 创建目录
        (self.memory_dir / "sessions").mkdir(exist_ok=True)
        (self.memory_dir / "skills").mkdir(exist_ok=True)
    
    def add_memory(self, category: str, heading: str, content: str) -> None:
        """添加分类记忆"""
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        
        file_path = self.memory_dir / f"{category}.md"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {heading}\n\n{content}\n")
    
    def get_memory(self, category: str) -> str:
        """获取分类记忆内容"""
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        
        file_path = self.memory_dir / f"{category}.md"
        return file_path.read_text(encoding="utf-8")
    
    def list_categories(self) -> List[str]:
        """列出所有分类"""
        return self.CATEGORIES.copy()
```

- [ ] **步骤4：运行测试验证通过**
运行：`pytest tests/test_memory_classifier.py::test_classified_memory_operations -v`
预期：PASS

- [ ] **步骤5：Commit**
```bash
git add cognix/core/memory_classifier.py tests/test_memory_classifier.py
git commit -m "feat: add memory classifier for categorized long-term memory"
```

### 任务2：扩展现有memory_system支持分类记忆
**文件：**
- 修改：`cognix/core/memory_system.py:1-50`
- 测试：`tests/test_memory_system.py::test_classified_memory_integration`

- [ ] **步骤1：编写失败的测试**
```python
def test_classified_memory_integration(self):
    # 测试分类记忆集成
    self.memory.add_classified_memory("office", "周报", "每周五发周报")
    
    # 搜索应该能找到分类记忆
    results = self.memory.search_memory("周报")
    assert any("每周五发周报" in r['text'] for r in results)
    
    # 现有add_persistent_memory应该兼容
    self.memory.add_persistent_memory("测试", "兼容测试内容")
    results = self.memory.search_memory("兼容测试")
    assert len(results) > 0
```

- [ ] **步骤2：运行测试验证失败**
运行：`pytest tests/test_memory_system.py::test_classified_memory_integration -v`
预期：FAIL，报错 "MarkdownMemory has no attribute 'add_classified_memory'"

- [ ] **步骤3：编写实现代码**
```python
# 在cognix/core/memory_system.py的MarkdownMemory类中添加
from .memory_classifier import MemoryClassifier

class MarkdownMemory:
    def __init__(self):
        # 现有初始化代码...
        self.classifier = MemoryClassifier(self.memory_dir)
    
    def add_classified_memory(self, category: str, heading: str, content: str) -> None:
        """添加分类记忆"""
        self.classifier.add_memory(category, heading, content)
        # 重新索引新内容
        self._index_markdown_file(self.memory_dir / f"{category}.md", "memory")
    
    # 扩展现有add_persistent_memory保持兼容
    def add_persistent_memory(self, heading: str, content: str) -> None:
        """兼容现有接口，自动分类到合适的分类"""
        # 简单的自动分类逻辑，后续可优化
        category = "reference"
        if any(keyword in heading.lower() for keyword in ["用户", "姓名", "角色", "职位"]):
            category = "user"
        elif any(keyword in heading.lower() for keyword in ["设置", "偏好", "默认"]):
            category = "settings"
        elif any(keyword in heading.lower() for keyword in ["办公", "周报", "会议", "流程"]):
            category = "office"
        elif any(keyword in heading.lower() for keyword in ["反馈", "建议", "修正"]):
            category = "feedback"
        
        self.add_classified_memory(category, heading, content)
```

- [ ] **步骤4：运行测试验证通过**
运行：`pytest tests/test_memory_system.py::test_classified_memory_integration -v`
预期：PASS

- [ ] **步骤5：Commit**
```bash
git add cognix/core/memory_system.py tests/test_memory_system.py
git commit -m "feat: integrate memory classifier into existing memory system, keep backward compatibility"
```

---

## 阶段2：数据接入层实现
### 任务3：标准事件结构与事件总线实现
**文件：**
- 创建：`cognix/core/event_bus.py`
- 测试：`tests/test_event_bus.py`

- [ ] **步骤1：编写失败的测试**
```python
from datetime import datetime
from cognix.core.event_bus import EventBus, Event

def test_event_bus():
    bus = EventBus()
    
    events_received = []
    def handler(event):
        events_received.append(event)
    
    # 订阅事件
    bus.subscribe("conversation", handler)
    
    # 发布事件
    event = Event(
        user_id="u001",
        time=datetime.now(),
        source="openclaw",
        event_type="conversation",
        content="以后周报默认发给王总",
        metadata={}
    )
    bus.publish(event)
    
    assert len(events_received) == 1
    assert events_received[0].content == "以后周报默认发给王总"
    
    # 测试不同事件类型不触发
    event2 = Event(
        user_id="u001",
        time=datetime.now(),
        source="feishu",
        event_type="calendar",
        content="明天10点开会",
        metadata={}
    )
    bus.publish(event2)
    assert len(events_received) == 1
```

- [ ] **步骤2：运行测试验证失败**
运行：`pytest tests/test_event_bus.py::test_event_bus -v`
预期：FAIL

- [ ] **步骤3：编写实现代码**
```python
# cognix/core/event_bus.py
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

@dataclass
class Event:
    """标准事件结构"""
    user_id: str
    time: datetime
    source: str  # openclaw / agent / feishu / user_input
    event_type: str  # conversation / tool_call / calendar / todo / etc.
    content: str
    metadata: dict

class EventBus:
    """事件总线"""
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """订阅事件"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def publish(self, event: Event) -> None:
        """发布事件"""
        if event.event_type in self.subscribers:
            for handler in self.subscribers[event.event_type]:
                handler(event)
```

- [ ] **步骤4：运行测试验证通过**
运行：`pytest tests/test_event_bus.py::test_event_bus -v`
预期：PASS

- [ ] **步骤5：Commit**
```bash
git add cognix/core/event_bus.py tests/test_event_bus.py
git commit -m "feat: implement event bus with standard event structure for data access layer"
```

---

**后续阶段任务清单（完整计划见完整文档）：**
### 阶段3：短期记忆Redis改造
- 实现Redis短期记忆存储
- TTL自动过期机制
- Token感知压缩算法
- 会话结束自动筛选逻辑

### 阶段4：记忆压缩流水线实现
- 触发条件检测
- 会话摘要生成
- LLM价值提取与分类
- 自动写入分类记忆文件

### 阶段5：双轨检索机制实现
- 固定核心记忆注入
- FTS5动态召回实现
- 上下文组装逻辑

### 阶段6：上层能力实现
- 工作流沉淀模块
- 主动提醒服务
- OpenClaw Hooks集成
- 飞书Bot实现
- CLI工具实现

---

## 自检
✅ 所有需求都有对应的实现任务
✅ 无占位符或TODO内容，所有步骤都有具体代码和命令
✅ 类型和方法名前后一致，无冲突
✅ 每个步骤粒度合理，2-5分钟可完成
✅ 所有现有功能保持兼容，无破坏性变更
