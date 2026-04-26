from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

@dataclass
class Event:
    """
    标准事件结构 - 数据接入层统一输入格式
    所有来源的数据都转换为此结构进入系统
    """
    user_id: str
    time: datetime
    source: str  # 来源：openclaw / agent / feishu / user_input
    event_type: str  # 事件类型：conversation / tool_call / calendar / todo / message / document / etc.
    content: str  # 事件内容
    metadata: dict  # 扩展元数据

class EventBus:
    """
    事件总线 - 实现事件的订阅与发布
    作为数据接入层的核心，负责将不同来源的事件分发给各个处理模块
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        订阅指定类型的事件
        :param event_type: 事件类型，使用"*"订阅所有事件
        :param handler: 事件处理函数，接收Event作为唯一参数
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def publish(self, event: Event) -> None:
        """
        发布事件
        :param event: 要发布的事件对象
        """
        # 先通知订阅了该事件类型的处理者
        if event.event_type in self.subscribers:
            for handler in self.subscribers[event.event_type]:
                handler(event)
        
        # 再通知订阅了所有事件的处理者
        if "*" in self.subscribers:
            for handler in self.subscribers["*"]:
                handler(event)
    
    def get_subscribed_event_types(self) -> List[str]:
        """获取所有已订阅的事件类型"""
        return list(self.subscribers.keys())
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> bool:
        """
        取消订阅
        :param event_type: 事件类型
        :param handler: 要取消的处理函数
        :return: 是否成功取消
        """
        if event_type not in self.subscribers:
            return False
        
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            if not self.subscribers[event_type]:
                del self.subscribers[event_type]
            return True
        
        return False


# 全局事件总线实例
_global_bus: Optional[EventBus] = None

def get_global_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus
