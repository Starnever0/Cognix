from .scheduler import AutodreamScheduler
from .process import AutodreamProcess, get_autodream_process

# 全局调度器实例
_autodream_scheduler: AutodreamScheduler = None

def get_autodream_scheduler() -> AutodreamScheduler:
    """获取全局Autodream调度器实例"""
    global _autodream_scheduler
    if _autodream_scheduler is None:
        _autodream_scheduler = AutodreamScheduler()
    return _autodream_scheduler

def start_autodream(use_process: bool = True) -> None:
    """
    启动Autodream服务
    :param use_process: 是否使用独立进程运行，False则使用单线程模式（兼容旧版本）
    """
    from cognix.utils.config import config
    if not config.autodream_enabled:
        return
    
    if use_process:
        # 双进程模式
        process = get_autodream_process()
        if not process.is_running():
            process.start()
    else:
        # 单线程模式（兼容旧版本）
        scheduler = get_autodream_scheduler()
        scheduler.start(interval_hours=config.autodream_schedule_interval)

def stop_autodream() -> None:
    """停止Autodream服务"""
    # 先停止进程
    process = get_autodream_process()
    if process.is_running():
        process.stop()
    # 再停止单线程调度器
    global _autodream_scheduler
    if _autodream_scheduler:
        _autodream_scheduler.stop()
        _autodream_scheduler = None

__all__ = [
    "AutodreamScheduler", 
    "get_autodream_scheduler",
    "AutodreamProcess", 
    "get_autodream_process",
    "start_autodream",
    "stop_autodream"
]
