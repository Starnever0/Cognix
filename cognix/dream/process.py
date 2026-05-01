import multiprocessing
import time
from typing import Dict, Any
from cognix.dream.scheduler import AutodreamScheduler
from cognix.utils.config import config
from cognix.core.event_bus import Event

class AutodreamProcess:
    """
    Autodream独立后台进程
    实现和主Agent进程分离，所有记忆整理、习惯识别、预测等重负载逻辑都在独立进程中运行
    完全不阻塞主交互流程
    """
    def __init__(self):
        self._process = None
        self._event_queue = multiprocessing.Queue()
        self._running = False
    
    def _worker_process(self, queue):
        """后台工作进程入口"""
        scheduler = AutodreamScheduler()
        scheduler.start(interval_hours=config.autodream_schedule_interval)
        
        while self._running:
            try:
                # 非阻塞获取事件
                if not queue.empty():
                    event = queue.get(block=False)
                    if isinstance(event, Event):
                        # 分发事件给调度器处理
                        if event.event_type == "session_end":
                            scheduler._handle_session_end_event(event)
                        elif event.event_type == "short_term_threshold_reached":
                            scheduler._handle_threshold_event(event)
                        elif event.event_type == "manual_trigger":
                            scheduler.run_once(trigger_type="manual")
                
                # 降低CPU占用
                time.sleep(0.1)
            except Exception as e:
                # 后台进程异常不影响主进程，打日志继续运行
                import logging
                logging.getLogger(__name__).warning(f"Autodream后台进程异常: {str(e)}")
                time.sleep(1)
        
        # 退出前停止调度器
        scheduler.stop()
    
    def start(self):
        """启动后台进程"""
        if self._process and self._process.is_alive():
            return
        
        self._running = True
        self._process = multiprocessing.Process(
            target=self._worker_process,
            args=(self._event_queue,),
            daemon=True,
            name="cognix-autodream"
        )
        self._process.start()
    
    def stop(self):
        """停止后台进程"""
        self._running = False
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=5)
            self._process = None
    
    def send_event(self, event: Event):
        """发送事件到后台进程"""
        if self._process and self._process.is_alive():
            try:
                self._event_queue.put(event, block=False)
            except Exception:
                # 队列满了就丢事件，不影响主进程
                pass
    
    def is_running(self) -> bool:
        """检查后台进程是否在运行"""
        return self._process is not None and self._process.is_alive()


# 全局进程实例
_autodream_process_instance: AutodreamProcess = None

def get_autodream_process() -> AutodreamProcess:
    """获取全局Autodream后台进程实例"""
    global _autodream_process_instance
    if _autodream_process_instance is None:
        _autodream_process_instance = AutodreamProcess()
    return _autodream_process_instance
