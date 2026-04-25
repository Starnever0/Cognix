from abc import ABC, abstractmethod


class BaseHook(ABC):
    """Hook基类，定义事件监听接口"""

    @abstractmethod
    def on_event(self, event_type: str, data: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError
