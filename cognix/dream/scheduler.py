import threading
from datetime import datetime, timedelta
from typing import Dict
from cognix.core.deduplicator import MemoryDeduplicator
from cognix.core.conflict_resolver import ConflictResolver
from cognix.core.preference_extractor import PreferenceExtractor
from cognix.core.habit_extractor import HabitExtractor
from cognix.core.skill_evolution import SkillEvolution
from cognix.core.insight_engine import InsightEngine
from cognix.core.memory_compressor import MemoryCompressor
from cognix.core.memory_system import get_memory_system
from cognix.core.event_bus import Event, get_global_event_bus
from cognix.utils.config import config


class AutodreamScheduler:
    """Autodream定时整理调度器 - 协调去重/冲突解决/偏好提取"""

    def __init__(self):
        self._deduplicator = MemoryDeduplicator()
        self._conflict_resolver = ConflictResolver()
        self._preference_extractor = PreferenceExtractor()
        self._habit_extractor = HabitExtractor()
        self._skill_evolution = SkillEvolution()
        self._insight_engine = InsightEngine()
        self._memory_compressor = MemoryCompressor()
        self._memory_system = get_memory_system()
        self._event_bus = get_global_event_bus()
        self._timer = None
        self._running = False
        # 自动订阅事件
        self._subscribe_events()

    def run_once(self, trigger_type: str = "scheduled") -> Dict:
        """
        执行完整的autodream流水线
        :param trigger_type: 触发类型：scheduled/event_triggered/manual
        """
        # 功能未开启时直接返回
        if not config.autodream_enabled:
            return {
                "timestamp": datetime.now().isoformat(),
                "trigger_type": trigger_type,
                "status": "disabled",
                "message": "Autodream is disabled in config"
            }
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "trigger_type": trigger_type,
            "status": "success",
            "deduplication": self._run_deduplication(),
            "conflict_resolution": self._run_conflict_resolution(),
            "preference_extraction": self._run_preference_extraction(),
            "habit_extraction": self._run_habit_extraction(),
            "skill_evolution": self._run_skill_evolution(),
            "insight_generation": self._run_insight_generation(),
            "memory_compression": self._run_memory_compression(),
            "archive_cleanup": self._run_archive_cleanup(),
        }
        return report

    def start(self, interval_hours: int = 24):
        self._running = True
        self._schedule_next(interval_hours)

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self, interval_hours: int):
        if not self._running:
            return
        self._timer = threading.Timer(interval_hours * 3600, self._run_scheduled, args=[interval_hours])
        self._timer.daemon = True
        self._timer.start()

    def _run_scheduled(self, interval_hours: int):
        try:
            self.run_once()
        except Exception:
            pass
        self._schedule_next(interval_hours)

    def _run_deduplication(self) -> dict:
        duplicates = self._deduplicator.find_duplicates()
        merged = 0
        for dup in duplicates:
            ids = [item["id"] for item in dup["items"]]
            self._deduplicator.merge_duplicates(ids)
            merged += 1
        return {"found": len(duplicates), "merged": merged}

    def _run_conflict_resolution(self) -> dict:
        conflicts = self._conflict_resolver.find_conflicts()
        return {"found": len(conflicts), "pending": len(conflicts)}

    def _run_preference_extraction(self) -> dict:
        preferences = self._preference_extractor.extract_from_interactions()
        saved = self._preference_extractor.save_preferences(preferences)
        return {"extracted": len(preferences), "saved": saved}

    def _run_memory_compression(self) -> dict:
        """执行短期记忆压缩和自动分类"""
        compressed_count = self._memory_compressor.compress_all_pending()
        return {"compressed": compressed_count}

    def _run_archive_cleanup(self) -> dict:
        """执行记忆归档和清理：30天以上会话归档，180天以上清理"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        archived = self._memory_system.archive_old_sessions(thirty_days_ago)
        
        one_eighty_days_ago = datetime.now() - timedelta(days=180)
        deleted = self._memory_system.cleanup_archived_sessions(one_eighty_days_ago)
        
        return {"archived": archived, "deleted": deleted}

    def _run_habit_extraction(self) -> dict:
        """执行用户习惯提取"""
        habits = self._habit_extractor.extract_habits()
        return {"extracted": len(habits)}

    def _run_skill_evolution(self) -> dict:
        """执行技能进化流程：技能清理、优化建议"""
        # 清理长期未使用的技能
        cleaned = self._skill_evolution.cleanup_inactive_skills()
        
        # 后续可以添加自动生成技能、自动优化技能的逻辑
        return {"cleaned_inactive": cleaned}
        
    def _run_insight_generation(self) -> dict:
        """执行主动洞察生成"""
        insights = self._insight_engine.generate_insights()
        return {
            "total": len(insights),
            "optimization": len([i for i in insights if i["type"] == "optimization"]),
            "reminders": len([i for i in insights if i["type"] == "reminder"]),
            "skill_recommendations": len([i for i in insights if i["type"] == "skill_recommendation"]),
            "risk_warnings": len([i for i in insights if i["type"] == "risk_warning"])
        }

    def _subscribe_events(self):
        """订阅事件总线的相关事件，触发autodream执行"""
        # 会话结束事件触发单次整理
        self._event_bus.subscribe("session_end", self._handle_session_end_event)
        # 短期记忆达到阈值事件触发整理
        self._event_bus.subscribe("short_term_threshold_reached", self._handle_threshold_event)
    
    def _handle_session_end_event(self, event: Event):
        """处理会话结束事件，触发记忆整理"""
        try:
            self.run_once(trigger_type="event_triggered")
        except Exception:
            # 异常不影响主流程
            pass
    
    def _handle_threshold_event(self, event: Event):
        """处理短期记忆阈值达到事件，触发记忆整理"""
        try:
            self.run_once(trigger_type="event_triggered")
        except Exception:
            # 异常不影响主流程
            pass
