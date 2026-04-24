import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

logger = logging.getLogger(__name__)

class MarkdownStore:
    def __init__(self, memory_path: Path):
        self.memory_path = memory_path
        self.memory_path.mkdir(exist_ok=True)
        
        self.preferences_path = self.memory_path / "preferences.md"
        self.rules_path = self.memory_path / "rules.md"
        self.knowledge_path = self.memory_path / "knowledge.md"
        
        # 初始化模板文件
        self._init_template_files()
        
        # 文件哈希缓存，用于检测变更
        self._file_hashes = {}
        
        # 变更回调函数
        self._preferences_change_callbacks = []
        self._rules_change_callbacks = []
        
        # 启动文件监控
        self._start_file_watcher()
    
    def _init_template_files(self):
        """初始化模板文件，如果不存在则创建"""
        if not self.preferences_path.exists():
            self._write_preferences_template()
        
        if not self.rules_path.exists():
            self._write_rules_template()
        
        if not self.knowledge_path.exists():
            self._write_knowledge_template()
    
    def _write_preferences_template(self):
        """写入偏好配置模板"""
        content = """# 用户偏好配置
> 可直接编辑此文件修改偏好，保存后自动生效
> 格式说明：- `键名` = `值` # 描述（可选值：选项1/选项2）

## 基础配置
- `output_language` = `zh-CN` # 输出语言：zh-CN/en
- `timezone` = `Asia/Shanghai` # 时区
- `dnd_time_range` = `22:00-08:00` # 免打扰时间段
- `data_retention_days` = `365` # 事件数据保留天数

## 内容生成偏好
- `report_format` = `markdown` # 报告格式：markdown/table
- `report_style` = `concise` # 报告风格：concise/detail
- `report_length` = `medium` # 报告长度：short/medium/long
- `report_tone` = `formal` # 报告语气：formal/casual/humorous
- `report_include_charts` = `true` # 报告是否包含图表：true/false

## 周报场景偏好
- `weekly_report_time` = `周五 18:00` # 周报默认生成时间
- `weekly_report_receiver` = `` # 周报默认接收人，多个用逗号分隔
- `weekly_report_auto_send` = `false` # 周报是否自动发送：true/false
- `weekly_report_template` = `default` # 周报模板
- `weekly_report_content_dimensions` = `工作内容,成果,问题,计划` # 周报内容维度

## 会议场景偏好
- `meeting_reminder_before` = `10` # 会议提前提醒时间（分钟）
- `meeting_auto_pull_docs` = `true` # 是否自动拉取会议文档：true/false
- `meeting_auto_generate_minutes` = `true` # 是否自动生成会议纪要：true/false
- `meeting_minutes_template` = `default` # 会议纪要模板

## 通知偏好
- `notification_channel` = `feishu,cli` # 通知渠道，多个用逗号分隔：feishu/cli/email
- `notification_level` = `info` # 通知级别：info/warn/error
- `notification_show_preview` = `true` # 通知是否显示内容预览：true/false

## 隐私配置
- `collect_cli_history` = `true` # 是否采集CLI历史：true/false
- `collect_feishu_messages` = `true` # 是否采集飞书消息：true/false
- `upload_data_for_training` = `false` # 是否上传数据用于模型训练：true/false
- `sensitive_data_filter` = `true` # 是否启用敏感数据过滤：true/false

## 学习配置
- `rule_recommendation_sensitivity` = `medium` # 规则推荐灵敏度：low/medium/high
- `auto_generate_rule_suggestions` = `true` # 是否自动生成规则建议：true/false
- `new_rule_require_confirmation` = `true` # 新规则是否需要确认：true/false
- `learning_history_period_days` = `30` # 历史数据学习周期（天）

## 第三方集成配置
- `feishu_enable` = `true` # 是否启用飞书集成：true/false
- `calendar_sync_enable` = `false` # 是否启用日历同步：true/false
- `email_enable` = `false` # 是否启用邮件集成：true/false
"""
        with open(self.preferences_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _write_rules_template(self):
        """写入规则模板"""
        content = """# 自动化规则
> 可直接编辑此文件添加/修改规则，保存后自动加载
> 格式说明：
> ## 状态分组 (active/pending/disabled)
> 1. [规则名称] `cron: 分 时 日 月 周`
>    动作：动作描述
>    创建时间：YYYY-MM-DD

## 激活规则 (active)

## 待确认规则 (pending)

## 禁用规则 (disabled)
"""
        with open(self.rules_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _write_knowledge_template(self):
        """写入知识模板"""
        content = """# 个人知识库
> 可在此记录长期知识、常用信息等，系统会自动学习其中的内容
"""
        with open(self.knowledge_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希，用于检测变更"""
        import hashlib
        if not file_path.exists():
            return ""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _parse_preferences(self) -> Dict:
        """解析preferences.md文件，返回键值对"""
        preferences = {}
        if not self.preferences_path.exists():
            return preferences
        
        pattern = r'- `([^`]+)`\s*=\s*`([^`]*)`\s*(#.*)?'
        
        with open(self.preferences_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        matches = re.findall(pattern, content)
        for key, value, _ in matches:
            # 类型转换
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '', 1).isdigit():
                value = float(value)
            
            preferences[key] = value
        
        return preferences
    
    def _generate_preferences_content(self, preferences: Dict) -> str:
        """根据偏好字典生成preferences.md内容"""
        # 先读取现有内容，保留结构和注释，只更新值
        if self.preferences_path.exists():
            with open(self.preferences_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            pattern = r'(- `([^`]+)`\s*=\s*)`[^`]*`'
            
            def replace_value(match):
                prefix = match.group(1)
                key = match.group(2)
                if key in preferences:
                    value = preferences[key]
                    if isinstance(value, bool):
                        value_str = 'true' if value else 'false'
                    else:
                        value_str = str(value)
                    return f'{prefix}`{value_str}`'
                return match.group(0)
            
            content = re.sub(pattern, replace_value, content)
            return content
        else:
            # 文件不存在则重新生成
            self._write_preferences_template()
            return self._generate_preferences_content(preferences)
    
    def _parse_rules(self) -> List[Dict]:
        """解析rules.md文件，返回规则列表"""
        rules = []
        if not self.rules_path.exists():
            return rules
        
        with open(self.rules_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        current_status = None
        current_rule = None
        
        for line in lines:
            line = line.strip()
            
            # 匹配状态分组
            status_match = re.match(r'##\s+(.+?)\s*\((\w+)\)', line)
            if status_match:
                current_status = status_match.group(2)
                continue
            
            # 匹配规则行
            rule_match = re.match(r'(\d+)\.\s*\[([^\]]+)\]\s*`cron:\s*([^`]+)`', line)
            if rule_match and current_status:
                if current_rule:
                    rules.append(current_rule)
                
                rule_id = int(rule_match.group(1))
                name = rule_match.group(2)
                trigger = f"cron: {rule_match.group(3)}"
                
                current_rule = {
                    "id": rule_id,
                    "name": name,
                    "trigger": trigger,
                    "status": current_status,
                    "action": {},
                    "created_at": ""
                }
                continue
            
            # 匹配动作行
            if current_rule and line.startswith("动作："):
                action_str = line[3:].strip()
                # 简单解析动作，后续可以扩展
                current_rule["action"]["description"] = action_str
                continue
            
            # 匹配创建时间行
            if current_rule and line.startswith("创建时间："):
                current_rule["created_at"] = line[5:].strip()
                continue
        
        if current_rule:
            rules.append(current_rule)
        
        return rules
    
    def _generate_rules_content(self, rules: List[Dict]) -> str:
        """根据规则列表生成rules.md内容"""
        # 按状态分组
        rules_by_status = {
            "active": [],
            "pending": [],
            "disabled": []
        }
        
        for rule in rules:
            status = rule.get("status", "pending")
            if status in rules_by_status:
                rules_by_status[status].append(rule)
        
        content = """# 自动化规则
> 可直接编辑此文件添加/修改规则，保存后自动加载
> 格式说明：
> ## 状态分组 (active/pending/disabled)
> 1. [规则名称] `cron: 分 时 日 月 周`
>    动作：动作描述
>    创建时间：YYYY-MM-DD

"""
        
        for status, status_name in [("active", "激活规则"), ("pending", "待确认规则"), ("disabled", "禁用规则")]:
            content += f"## {status_name} ({status})\n"
            
            for i, rule in enumerate(rules_by_status[status], 1):
                trigger = rule["trigger"].replace("cron: ", "").strip()
                action_desc = rule.get("action", {}).get("description", "")
                created_at = rule.get("created_at", datetime.now().strftime("%Y-%m-%d"))
                
                content += f"{i}. [{rule['name']}] `cron: {trigger}`\n"
                content += f"   动作：{action_desc}\n"
                content += f"   创建时间：{created_at}\n\n"
            
            content += "\n"
        
        return content
    
    def get_preferences(self) -> Dict:
        """获取所有偏好"""
        return self._parse_preferences()
    
    def save_preferences(self, preferences: Dict):
        """保存偏好到文件"""
        content = self._generate_preferences_content(preferences)
        with open(self.preferences_path, "w", encoding="utf-8") as f:
            f.write(content)
        # 更新哈希缓存
        self._file_hashes[str(self.preferences_path)] = self._get_file_hash(self.preferences_path)
    
    def get_rules(self) -> List[Dict]:
        """获取所有规则"""
        return self._parse_rules()
    
    def save_rules(self, rules: List[Dict]):
        """保存规则到文件"""
        content = self._generate_rules_content(rules)
        with open(self.rules_path, "w", encoding="utf-8") as f:
            f.write(content)
        # 更新哈希缓存
        self._file_hashes[str(self.rules_path)] = self._get_file_hash(self.rules_path)
    
    def register_preferences_change_callback(self, callback):
        """注册偏好变更回调"""
        self._preferences_change_callbacks.append(callback)
    
    def register_rules_change_callback(self, callback):
        """注册规则变更回调"""
        self._rules_change_callbacks.append(callback)
    
    def _start_file_watcher(self):
        """启动文件监控"""
        class MarkdownFileHandler(FileSystemEventHandler):
            def __init__(self, store):
                self.store = store
            
            def on_modified(self, event):
                if event.is_directory:
                    return
                
                file_path = Path(event.src_path)
                file_key = str(file_path)
                
                # 检查文件是否真的变更（避免重复触发）
                current_hash = self.store._get_file_hash(file_path)
                if current_hash == self.store._file_hashes.get(file_key):
                    return
                
                self.store._file_hashes[file_key] = current_hash
                
                if file_path == self.store.preferences_path:
                    logger.info("检测到preferences.md变更，自动重新加载")
                    new_preferences = self.store._parse_preferences()
                    for callback in self.store._preferences_change_callbacks:
                        try:
                            callback(new_preferences)
                        except Exception as e:
                            logger.error(f"执行偏好变更回调失败: {e}")
                
                elif file_path == self.store.rules_path:
                    logger.info("检测到rules.md变更，自动重新加载")
                    new_rules = self.store._parse_rules()
                    for callback in self.store._rules_change_callbacks:
                        try:
                            callback(new_rules)
                        except Exception as e:
                            logger.error(f"执行规则变更回调失败: {e}")
        
        event_handler = MarkdownFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.memory_path), recursive=False)
        self.observer.start()
        
        # 初始化哈希缓存
        self._file_hashes[str(self.preferences_path)] = self._get_file_hash(self.preferences_path)
        self._file_hashes[str(self.rules_path)] = self._get_file_hash(self.rules_path)
    
    def stop(self):
        """停止文件监控"""
        if hasattr(self, 'observer'):
            self.observer.stop()
            self.observer.join()

from cognix.utils.config import config
markdown_store = MarkdownStore(config.memory_path)
