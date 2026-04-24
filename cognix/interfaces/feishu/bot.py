from lark_oapi import Client, JSON
from lark_oapi.api.im.v1 import *
from typing import Dict, Optional
from cognix.utils.config import config
from cognix.core.event_collector import event_collector
from cognix.core.rule_engine import rule_engine
from cognix.core.preference_store import preference_store
import json
import logging

logger = logging.getLogger(__name__)

class FeishuBot:
    def __init__(self):
        self.client = None
        if config.feishu_app_id and config.feishu_app_secret:
            self.client = Client.builder() \
                .app_id(config.feishu_app_id) \
                .app_secret(config.feishu_app_secret) \
                .build()
            logger.info("飞书 Bot 初始化成功")
        else:
            logger.warning("未配置飞书密钥，Bot 功能不可用")
    
    def is_available(self) -> bool:
        """检查飞书 Bot 是否可用"""
        return self.client is not None
    
    def send_text_message(self, receive_id_type: str, receive_id: str, content: str) -> bool:
        """发送文本消息
        :param receive_id_type: 接收ID类型：open_id/user_id/email/chat_id
        :param receive_id: 接收ID
        :param content: 消息内容
        """
        if not self.is_available():
            logger.warning("飞书 Bot 未配置，无法发送消息")
            return False
        
        req = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type("text")
                .content(JSON.dumps({"text": content}))
                .build()) \
            .build()
        
        resp = self.client.im.v1.message.create(req)
        if not resp.success():
            logger.error(f"发送飞书消息失败: {resp.msg}, request_id: {resp.get_request_id()}")
        return resp.success()
    
    def send_weekly_report_reminder(self, user_open_id: str, format: str, receiver: str) -> bool:
        """发送周报提醒交互式卡片
        :param user_open_id: 用户飞书 OpenID
        :param format: 周报格式
        :param receiver: 周报接收人
        """
        if not self.is_available():
            return False
        
        card_content = {
            "config": {
                "wide_screen_mode": True
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"📅 今天是周五，已按你偏好的 **{format}** 格式生成本周周报草稿，是否发送给 **{receiver}**？",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"content": "立即发送", "tag": "plain_text"},
                            "type": "primary",
                            "value": {"action": "confirm_weekly_report", "format": format, "receiver": receiver}
                        },
                        {
                            "tag": "button",
                            "text": {"content": "稍后再说", "tag": "plain_text"},
                            "type": "default",
                            "value": {"action": "reject_weekly_report"}
                        },
                        {
                            "tag": "button",
                            "text": {"content": "修改设置", "tag": "plain_text"},
                            "type": "default",
                            "value": {"action": "modify_weekly_report"}
                        }
                    ]
                }
            ],
            "header": {
                "title": {
                    "content": "🔔 周报提醒",
                    "tag": "plain_text"
                },
                "template": "blue"
            }
        }
        
        req = CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(user_open_id)
                .msg_type("interactive")
                .content(JSON.dumps(card_content))
                .build()) \
            .build()
        
        resp = self.client.im.v1.message.create(req)
        if not resp.success():
            logger.error(f"发送周报提醒卡片失败: {resp.msg}")
        return resp.success()
    
    def send_meeting_reminder(self, user_open_id: str, meeting_time: str, before_minutes: int, content: str) -> bool:
        """发送会议提醒卡片
        :param user_open_id: 用户飞书 OpenID
        :param meeting_time: 会议时间
        :param before_minutes: 提前提醒分钟数
        :param content: 准备内容
        """
        if not self.is_available():
            return False
        
        card_content = {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"⏰ 距离会议还有 **{before_minutes}** 分钟\n会议时间：{meeting_time}\n准备内容：{content}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"content": "打开文档", "tag": "plain_text"},
                            "type": "primary",
                            "value": {"action": "open_meeting_doc"}
                        },
                        {
                            "tag": "button",
                            "text": {"content": "知道了", "tag": "plain_text"},
                            "type": "default",
                            "value": {"action": "dismiss_reminder"}
                        }
                    ]
                }
            ],
            "header": {
                "title": {
                    "content": "会议提醒",
                    "tag": "plain_text"
                },
                "template": "orange"
            }
        }
        
        req = CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(user_open_id)
                .msg_type("interactive")
                .content(JSON.dumps(card_content))
                .build()) \
            .build()
        
        resp = self.client.im.v1.message.create(req)
        return resp.success()
    
    def handle_event(self, event: Dict) -> Optional[Dict]:
        """处理飞书事件回调
        :param event: 飞书回调事件
        :return: 响应内容
        """
        if not self.is_available():
            return {"code": -1, "msg": "飞书 Bot 未配置"}
        
        header = event.get("header", {})
        event_type = header.get("event_type")
        event_data = event.get("event", {})
        
        if not event_type:
            return {"code": 0}
        
        # 处理消息接收事件
        if event_type == "im.message.receive_v1":
            message = event_data.get("message", {})
            sender = event_data.get("sender", {})
            content = json.loads(message.get("content", "{}")).get("text", "")
            user_open_id = sender.get("sender_id", {}).get("open_id", "")
            
            # 记录事件
            event_collector.track_feishu_interaction(
                "message_receive", 
                user_open_id, 
                {"content": content, "message_id": message.get("message_id")}
            )
            
            # 关键词响应
            if "周报" in content:
                if "生成" in content or "写" in content:
                    fmt = preference_store.get_report_format()
                    receiver = preference_store.get_weekly_report_receiver()
                    self.send_weekly_report_reminder(user_open_id, fmt, receiver)
                    return {"code": 0}
            
            # 帮助响应
            if "帮助" in content or "help" in content.lower():
                help_text = """🤖 Cognix 助手使用指南：
1. 说「生成周报」获取周报提醒
2. 配置周报接收人：/set receiver 负责人名字
3. 配置输出格式：/set format table/markdown
4. 查看当前配置：/config
                """
                self.send_text_message("open_id", user_open_id, help_text)
                return {"code": 0}
        
        # 处理卡片按钮点击事件
        elif event_type == "im.message.action.triggered_v1":
            action = event_data.get("action", {})
            action_value = action.get("value", {})
            user_open_id = event_data.get("operator", {}).get("open_id", "")
            
            # 记录事件
            event_collector.track_feishu_interaction(
                "action_click", 
                user_open_id, 
                {"action": action_value}
            )
            
            action_type = action_value.get("action")
            if action_type == "confirm_weekly_report":
                # 确认发送周报
                fmt = action_value.get("format", "table")
                receiver = action_value.get("receiver", "")
                preference_store.set("report_format", {"value": fmt})
                preference_store.set("weekly_report_receiver", {"value": receiver})
                self.send_text_message("open_id", user_open_id, "✅ 周报已发送，相关偏好已保存")
                
                # 检查是否需要自动创建周报规则
                recent_events = event_collector.store.get_events(event_type="feishu_interaction", limit=5)
                weekly_count = sum(1 for e in recent_events if e["data"].get("action", {}).get("action") == "confirm_weekly_report")
                if weekly_count >= 3:
                    existing_rules = rule_engine.get_all_rules()
                    has_weekly_rule = any("周报" in r["name"] for r in existing_rules)
                    if not has_weekly_rule:
                        rule_id = rule_engine.generate_weekly_report_rule()
                        self.send_text_message("open_id", user_open_id, f"💡 检测到你每周都会生成周报，已自动创建周报提醒规则（ID: {rule_id}），确认后每周自动提醒")
            
            elif action_type == "reject_weekly_report":
                self.send_text_message("open_id", user_open_id, "👌 已取消发送")
            
            elif action_type == "modify_weekly_report":
                self.send_text_message("open_id", user_open_id, "请使用命令修改偏好：\n设置格式：/set format markdown\n设置接收人：/set receiver 新的接收人")
        
        return {"code": 0}

feishu_bot = FeishuBot()
