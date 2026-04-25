from cognix.hooks.base import BaseHook
from cognix.hooks.feishu_hook import FeishuHook
from cognix.hooks.context_threshold import ContextThresholdHook


class HookRegistry:
    def __init__(self):
        self._hooks: dict[str, BaseHook] = {}
        self._register_default_hooks()

    def _register_default_hooks(self):
        self.register(FeishuHook())
        self.register(ContextThresholdHook())

    def register(self, hook: BaseHook):
        self._hooks[hook.name] = hook

    def unregister(self, name: str):
        if name in self._hooks:
            self._hooks[name].stop()
            del self._hooks[name]

    def start_all(self):
        for hook in self._hooks.values():
            hook.start()

    def stop_all(self):
        for hook in self._hooks.values():
            hook.stop()

    def dispatch(self, event_type: str, data: dict):
        for hook in self._hooks.values():
            try:
                hook.on_event(event_type, data)
            except Exception:
                pass

    def list_hooks(self) -> list[str]:
        return list(self._hooks.keys())

    def get_hook(self, name: str) -> BaseHook | None:
        return self._hooks.get(name)
