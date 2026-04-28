from .scheduler import AutodreamScheduler

# 全局调度器实例
_autodream_scheduler: AutodreamScheduler = None

def get_autodream_scheduler() -> AutodreamScheduler:
    """获取全局Autodream调度器实例"""
    global _autodream_scheduler
    if _autodream_scheduler is None:
        _autodream_scheduler = AutodreamScheduler()
    return _autodream_scheduler

__all__ = ["AutodreamScheduler", "get_autodream_scheduler"]
