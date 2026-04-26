from datetime import datetime
import pytest
from cognix.core.event_bus import EventBus, Event

def test_event_creation():
    """测试事件创建"""
    event = Event(
        user_id="u001",
        time=datetime.now(),
        source="openclaw",
        event_type="conversation",
        content="以后周报默认发给王总",
        metadata={"session_id": "test-123"}
    )
    
    assert event.user_id == "u001"
    assert event.source == "openclaw"
    assert event.event_type == "conversation"
    assert event.content == "以后周报默认发给王总"
    assert event.metadata["session_id"] == "test-123"

def test_event_bus_subscribe_publish():
    """测试事件总线订阅发布"""
    bus = EventBus()
    
    events_received = []
    
    def conversation_handler(event):
        events_received.append(("conversation", event))
    
    def tool_call_handler(event):
        events_received.append(("tool_call", event))
    
    # 订阅事件
    bus.subscribe("conversation", conversation_handler)
    bus.subscribe("tool_call", tool_call_handler)
    
    # 发布conversation事件
    event1 = Event(
        user_id="u001",
        time=datetime.now(),
        source="openclaw",
        event_type="conversation",
        content="测试对话",
        metadata={}
    )
    bus.publish(event1)
    
    assert len(events_received) == 1
    assert events_received[0][0] == "conversation"
    assert events_received[0][1].content == "测试对话"
    
    # 发布tool_call事件
    event2 = Event(
        user_id="u001",
        time=datetime.now(),
        source="agent",
        event_type="tool_call",
        content="调用git status",
        metadata={"tool": "git"}
    )
    bus.publish(event2)
    
    assert len(events_received) == 2
    assert events_received[1][0] == "tool_call"
    assert events_received[1][1].metadata["tool"] == "git"
    
    # 发布其他类型事件，不应该触发
    event3 = Event(
        user_id="u001",
        time=datetime.now(),
        source="feishu",
        event_type="calendar",
        content="明天开会",
        metadata={}
    )
    bus.publish(event3)
    
    assert len(events_received) == 2  # 数量不变

def test_event_bus_multiple_subscribers():
    """测试同一个事件多个订阅者"""
    bus = EventBus()
    
    count1 = 0
    count2 = 0
    
    def handler1(event):
        nonlocal count1
        count1 += 1
    
    def handler2(event):
        nonlocal count2
        count2 += 1
    
    bus.subscribe("test_event", handler1)
    bus.subscribe("test_event", handler2)
    
    event = Event(
        user_id="u001",
        time=datetime.now(),
        source="test",
        event_type="test_event",
        content="test",
        metadata={}
    )
    
    bus.publish(event)
    
    assert count1 == 1
    assert count2 == 1
