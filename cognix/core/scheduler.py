from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Dict, Optional, List
import re
from cognix.core.rule_engine import rule_engine
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self.action_handlers = {}
        self._load_active_rules()
    
    def register_action_handler(self, action_type: str, handler: Callable):
        """注册动作处理器
        :param action_type: 动作类型，如 weekly_report/meeting_reminder
        :param handler: 处理函数，接收 action 字典作为参数
        """
        self.action_handlers[action_type] = handler
    
    def _parse_trigger(self, trigger_str: str) -> Optional[CronTrigger]:
        """解析触发表达式，支持 cron 格式
        支持格式：cron: * * * * *（分 时 日 月 周）
        """
        if trigger_str.startswith("cron: "):
            cron_expr = trigger_str[6:].strip()
            parts = cron_expr.split()
            if len(parts) == 5:
                return CronTrigger(
                    minute=parts[0], 
                    hour=parts[1], 
                    day=parts[2], 
                    month=parts[3], 
                    day_of_week=parts[4],
                    timezone="Asia/Shanghai"
                )
        return None
    
    def _execute_action(self, action: Dict):
        """执行动作"""
        action_type = action.get("type")
        if not action_type:
            logger.warning(f"动作缺少类型：{action}")
            return
        
        if action_type in self.action_handlers:
            try:
                logger.info(f"执行动作：{action_type}")
                self.action_handlers[action_type](action)
            except Exception as e:
                logger.error(f"执行动作失败：{e}", exc_info=True)
        else:
            logger.warning(f"未找到动作处理器：{action_type}")
    
    def _load_active_rules(self):
        """加载所有激活的规则"""
        rules = rule_engine.get_active_rules()
        for rule in rules:
            trigger = self._parse_trigger(rule["trigger"])
            if trigger:
                job_id = f"rule_{rule['id']}"
                self.scheduler.add_job(
                    self._execute_action,
                    trigger=trigger,
                    args=[rule["action"]],
                    id=job_id,
                    replace_existing=True,
                    name=rule["name"]
                )
                logger.info(f"加载规则：{rule['name']} (ID: {rule['id']})")
            else:
                logger.warning(f"无效的触发表达式：{rule['trigger']} (规则ID: {rule['id']})")
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("调度器已启动")
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("调度器已停止")
    
    def reload_rules(self):
        """重新加载所有规则"""
        self.scheduler.remove_all_jobs()
        self._load_active_rules()
        logger.info("规则已重新加载")
    
    def get_jobs(self) -> List[Dict]:
        """获取所有运行中的任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

scheduler = Scheduler()
