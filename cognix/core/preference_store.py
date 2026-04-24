from typing import Dict, Optional, List, Any
from cognix.storage.sqlite_store import sqlite_store
from cognix.storage.markdown_store import markdown_store
import json
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 偏好元数据定义
PREFERENCE_METADATA = {
    # 基础配置
    "output_language": {
        "type": "string",
        "default": "zh-CN",
        "options": ["zh-CN", "en"],
        "description": "输出语言",
        "category": "基础配置"
    },
    "timezone": {
        "type": "string",
        "default": "Asia/Shanghai",
        "description": "时区",
        "category": "基础配置"
    },
    "dnd_time_range": {
        "type": "string",
        "default": "22:00-08:00",
        "description": "免打扰时间段",
        "category": "基础配置"
    },
    "data_retention_days": {
        "type": "integer",
        "default": 365,
        "min": 30,
        "max": 3650,
        "description": "事件数据保留天数",
        "category": "基础配置"
    },
    
    # 内容生成偏好
    "report_format": {
        "type": "string",
        "default": "markdown",
        "options": ["markdown", "table"],
        "description": "报告格式",
        "category": "内容生成偏好"
    },
    "report_style": {
        "type": "string",
        "default": "concise",
        "options": ["concise", "detail"],
        "description": "报告风格",
        "category": "内容生成偏好"
    },
    "report_length": {
        "type": "string",
        "default": "medium",
        "options": ["short", "medium", "long"],
        "description": "报告长度",
        "category": "内容生成偏好"
    },
    "report_tone": {
        "type": "string",
        "default": "formal",
        "options": ["formal", "casual", "humorous"],
        "description": "报告语气",
        "category": "内容生成偏好"
    },
    "report_include_charts": {
        "type": "boolean",
        "default": True,
        "description": "报告是否包含图表",
        "category": "内容生成偏好"
    },
    
    # 周报场景偏好
    "weekly_report_time": {
        "type": "string",
        "default": "周五 18:00",
        "description": "周报默认生成时间",
        "category": "周报场景偏好"
    },
    "weekly_report_receiver": {
        "type": "string",
        "default": "",
        "description": "周报默认接收人，多个用逗号分隔",
        "category": "周报场景偏好"
    },
    "weekly_report_auto_send": {
        "type": "boolean",
        "default": False,
        "description": "周报是否自动发送",
        "category": "周报场景偏好"
    },
    "weekly_report_template": {
        "type": "string",
        "default": "default",
        "description": "周报模板",
        "category": "周报场景偏好"
    },
    "weekly_report_content_dimensions": {
        "type": "string",
        "default": "工作内容,成果,问题,计划",
        "description": "周报内容维度",
        "category": "周报场景偏好"
    },
    
    # 会议场景偏好
    "meeting_reminder_before": {
        "type": "integer",
        "default": 10,
        "min": 1,
        "max": 60,
        "description": "会议提前提醒时间（分钟）",
        "category": "会议场景偏好"
    },
    "meeting_auto_pull_docs": {
        "type": "boolean",
        "default": True,
        "description": "是否自动拉取会议文档",
        "category": "会议场景偏好"
    },
    "meeting_auto_generate_minutes": {
        "type": "boolean",
        "default": True,
        "description": "是否自动生成会议纪要",
        "category": "会议场景偏好"
    },
    "meeting_minutes_template": {
        "type": "string",
        "default": "default",
        "description": "会议纪要模板",
        "category": "会议场景偏好"
    },
    
    # 通知偏好
    "notification_channel": {
        "type": "string",
        "default": "feishu,cli",
        "description": "通知渠道，多个用逗号分隔：feishu/cli/email",
        "category": "通知偏好"
    },
    "notification_level": {
        "type": "string",
        "default": "info",
        "options": ["info", "warn", "error"],
        "description": "通知级别",
        "category": "通知偏好"
    },
    "notification_show_preview": {
        "type": "boolean",
        "default": True,
        "description": "通知是否显示内容预览",
        "category": "通知偏好"
    },
    
    # 隐私配置
    "collect_cli_history": {
        "type": "boolean",
        "default": True,
        "description": "是否采集CLI历史",
        "category": "隐私配置"
    },
    "collect_feishu_messages": {
        "type": "boolean",
        "default": True,
        "description": "是否采集飞书消息",
        "category": "隐私配置"
    },
    "upload_data_for_training": {
        "type": "boolean",
        "default": False,
        "description": "是否上传数据用于模型训练",
        "category": "隐私配置"
    },
    "sensitive_data_filter": {
        "type": "boolean",
        "default": True,
        "description": "是否启用敏感数据过滤",
        "category": "隐私配置"
    },
    
    # 学习配置
    "rule_recommendation_sensitivity": {
        "type": "string",
        "default": "medium",
        "options": ["low", "medium", "high"],
        "description": "规则推荐灵敏度",
        "category": "学习配置"
    },
    "auto_generate_rule_suggestions": {
        "type": "boolean",
        "default": True,
        "description": "是否自动生成规则建议",
        "category": "学习配置"
    },
    "new_rule_require_confirmation": {
        "type": "boolean",
        "default": True,
        "description": "新规则是否需要确认",
        "category": "学习配置"
    },
    "learning_history_period_days": {
        "type": "integer",
        "default": 30,
        "min": 7,
        "max": 180,
        "description": "历史数据学习周期（天）",
        "category": "学习配置"
    },
    
    # 第三方集成配置
    "feishu_enable": {
        "type": "boolean",
        "default": True,
        "description": "是否启用飞书集成",
        "category": "第三方集成配置"
    },
    "calendar_sync_enable": {
        "type": "boolean",
        "default": False,
        "description": "是否启用日历同步",
        "category": "第三方集成配置"
    },
    "email_enable": {
        "type": "boolean",
        "default": False,
        "description": "是否启用邮件集成",
        "category": "第三方集成配置"
    }
}

# 分类列表
PREFERENCE_CATEGORIES = list({meta["category"] for meta in PREFERENCE_METADATA.values()})

class PreferenceStore:
    def __init__(self):
        self.store = sqlite_store
        self.md_store = markdown_store
        self._sync_from_md()
        
        # 注册MD文件变更回调
        self.md_store.register_preferences_change_callback(self._on_preferences_changed)
    
    def _validate_value(self, key: str, value: Any) -> tuple[bool, Any]:
        """验证偏好值是否合法"""
        if key not in PREFERENCE_METADATA:
            return False, f"未知偏好键：{key}"
        
        meta = PREFERENCE_METADATA[key]
        expected_type = meta["type"]
        
        # 类型校验
        if expected_type == "integer":
            if not isinstance(value, int):
                try:
                    value = int(value)
                except:
                    return False, f"{key} 应为整数类型"
            if "min" in meta and value < meta["min"]:
                return False, f"{key} 最小值为 {meta['min']}"
            if "max" in meta and value > meta["max"]:
                return False, f"{key} 最大值为 {meta['max']}"
        
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    return False, f"{key} 应为布尔类型"
        
        elif expected_type == "string":
            if not isinstance(value, str):
                value = str(value)
            if "options" in meta and value not in meta["options"]:
                return False, f"{key} 可选值为：{', '.join(meta['options'])}"
        
        return True, value
    
    def _sync_from_md(self):
        """从Markdown文件同步偏好到SQLite"""
        try:
            md_preferences = self.md_store.get_preferences()
            for key, value in md_preferences.items():
                # 验证值
                valid, validated_value = self._validate_value(key, value)
                if not valid:
                    logger.warning(f"偏好 {key} 值不合法，跳过同步：{validated_value}")
                    continue
                
                # 保存到SQLite
                self.store.set_preference(key, {"value": validated_value}, md_hash=self.md_store._get_file_hash(self.md_store.preferences_path))
            
            logger.info("偏好已从Markdown文件同步完成")
        except Exception as e:
            logger.error(f"从Markdown同步偏好失败：{e}")
    
    def _sync_to_md(self):
        """将SQLite中的偏好同步到Markdown文件"""
        try:
            preferences = {}
            for pref in self.store.list_preferences():
                preferences[pref["key"]] = pref["value"]["value"]
            
            # 补充默认值
            for key, meta in PREFERENCE_METADATA.items():
                if key not in preferences:
                    preferences[key] = meta["default"]
            
            self.md_store.save_preferences(preferences)
            logger.info("偏好已同步到Markdown文件")
        except Exception as e:
            logger.error(f"同步偏好到Markdown失败：{e}")
    
    def _on_preferences_changed(self, new_preferences: Dict):
        """MD文件变更回调"""
        logger.info("检测到Markdown偏好文件变更，重新同步")
        self._sync_from_md()
    
    def set(self, key: str, value: Any, weight: float = 1.0) -> Optional[Dict]:
        """设置用户偏好
        :param key: 偏好键名
        :param value: 偏好值
        :param weight: 偏好权重，0-1，越高优先级越高
        """
        # 验证值
        valid, validated_value = self._validate_value(key, value)
        if not valid:
            raise ValueError(validated_value)
        
        old_value = self.get(key)
        if old_value:
            # 偏好更新时权重增加
            weight = min(weight + 0.1, 1.0)
        
        self.store.set_preference(key, {"value": validated_value}, weight)
        
        # 同步到MD
        self._sync_to_md()
        
        return {"value": old_value} if old_value is not None else None
    
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """获取用户偏好"""
        result = self.store.get_preference(key)
        if result:
            return result["value"]["value"]
        
        # 没有的话返回默认值
        if key in PREFERENCE_METADATA:
            return PREFERENCE_METADATA[key]["default"]
        
        return default
    
    def get_with_meta(self, key: str) -> Optional[Dict]:
        """获取偏好包含元信息"""
        result = self.store.get_preference(key)
        if not result and key in PREFERENCE_METADATA:
            meta = PREFERENCE_METADATA[key]
            return {
                "key": key,
                "value": meta["default"],
                "weight": 1.0,
                "meta": meta
            }
        
        if result:
            return {
                "key": key,
                "value": result["value"]["value"],
                "weight": result["weight"],
                "meta": PREFERENCE_METADATA.get(key, {})
            }
        
        return None
    
    def list(self, category: Optional[str] = None) -> List[Dict]:
        """列出所有偏好
        :param category: 按分类筛选
        """
        preferences = self.store.list_preferences()
        pref_dict = {p["key"]: p for p in preferences}
        
        result = []
        for key, meta in PREFERENCE_METADATA.items():
            if category and meta["category"] != category:
                continue
            
            if key in pref_dict:
                pref = pref_dict[key]
                result.append({
                    "key": key,
                    "value": pref["value"]["value"],
                    "weight": pref["weight"],
                    "category": meta["category"],
                    "description": meta["description"],
                    "created_at": pref["created_at"],
                    "updated_at": pref["updated_at"]
                })
            else:
                # 使用默认值
                result.append({
                    "key": key,
                    "value": meta["default"],
                    "weight": 1.0,
                    "category": meta["category"],
                    "description": meta["description"],
                    "created_at": None,
                    "updated_at": None
                })
        
        return result
    
    def delete(self, key: str) -> bool:
        """删除指定偏好"""
        exists = self.get(key) is not None
        if exists:
            self.store.delete_preference(key)
            self._sync_to_md()
        return exists
    
    def export(self, file_path: str, format: str = "json") -> bool:
        """导出偏好到文件
        :param file_path: 导出文件路径
        :param format: 导出格式：json/md
        """
        try:
            preferences = {}
            for pref in self.list():
                preferences[pref["key"]] = pref["value"]
            
            if format.lower() == "json":
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(preferences, f, ensure_ascii=False, indent=2)
            
            elif format.lower() == "md":
                # 使用markdown_store生成格式
                self.md_store.save_preferences(preferences)
                import shutil
                shutil.copy(self.md_store.preferences_path, file_path)
            
            else:
                raise ValueError(f"不支持的导出格式：{format}")
            
            return True
        except Exception as e:
            logger.error(f"导出偏好失败：{e}")
            return False
    
    def import_file(self, file_path: str, format: Optional[str] = None) -> tuple[bool, str]:
        """从文件导入偏好
        :param file_path: 导入文件路径
        :param format: 导入格式：json/md，自动检测后缀
        """
        try:
            if not format:
                if file_path.endswith(".json"):
                    format = "json"
                elif file_path.endswith(".md"):
                    format = "md"
                else:
                    return False, "无法自动检测文件格式，请指定format参数"
            
            preferences = {}
            if format == "json":
                with open(file_path, "r", encoding="utf-8") as f:
                    preferences = json.load(f)
            
            elif format == "md":
                # 临时解析MD文件
                from cognix.storage.markdown_store import MarkdownStore
                import tempfile
                temp_dir = tempfile.mkdtemp()
                temp_store = MarkdownStore(Path(temp_dir))
                # 复制文件到临时目录
                import shutil
                shutil.copy(file_path, temp_store.preferences_path)
                preferences = temp_store.get_preferences()
                temp_store.stop()
                shutil.rmtree(temp_dir)
            
            # 验证并导入
            for key, value in preferences.items():
                valid, validated_value = self._validate_value(key, value)
                if not valid:
                    return False, f"偏好 {key} 验证失败：{validated_value}"
                
                self.set(key, validated_value)
            
            return True, "导入成功"
        except Exception as e:
            return False, f"导入失败：{str(e)}"
    
    def reset(self, category: Optional[str] = None) -> bool:
        """重置偏好为默认值
        :param category: 重置指定分类的偏好，不指定则重置所有
        """
        try:
            if category:
                # 重置指定分类
                for key, meta in PREFERENCE_METADATA.items():
                    if meta["category"] == category:
                        self.set(key, meta["default"], 1.0)
            else:
                # 重置所有
                for key, meta in PREFERENCE_METADATA.items():
                    self.set(key, meta["default"], 1.0)
            
            return True
        except Exception as e:
            logger.error(f"重置偏好失败：{e}")
            return False
    
    # 原有快捷方法保持兼容
    def get_report_format(self) -> str:
        """获取报告输出格式，默认 table"""
        return str(self.get("report_format", "table"))
    
    def get_weekly_report_receiver(self) -> str:
        """获取周报接收人"""
        return str(self.get("weekly_report_receiver", ""))
    
    def get_meeting_reminder_time(self) -> int:
        """获取会议提醒提前时间（分钟），默认 5 分钟"""
        return int(self.get("meeting_reminder_before", 5))
    
    def get_output_language(self) -> str:
        """获取输出语言，默认中文"""
        return str(self.get("output_language", "zh-CN"))
    
    def get_dnd_time_range(self) -> tuple:
        """获取免打扰时间段，默认 (22:00, 08:00)"""
        dnd_str = str(self.get("dnd_time_range", "22:00-08:00"))
        try:
            start, end = dnd_str.split("-")
            return (start.strip(), end.strip())
        except:
            return ("22:00", "08:00")

preference_store = PreferenceStore()
