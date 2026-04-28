import json
from typing import Optional
from cognix.utils.config import config


class FeishuClient:
    """飞书API客户端 - 封装消息发送与事件验证"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import lark_oapi as lark
                from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

                self._client = lark.Client.builder() \
                    .app_id(config.feishu_app_id) \
                    .app_secret(config.feishu_app_secret) \
                    .build()
            except ImportError:
                self._client = None
        return self._client

    def is_available(self) -> bool:
        return bool(config.feishu_app_id and config.feishu_app_secret and self.client)

    def send_text_message(self, receive_id_type: str, receive_id: str, text: str) -> bool:
        if not self.is_available():
            return False

        try:
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

            req = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("text")
                    .content(json.dumps({"text": text}))
                    .build()) \
                .build()

            resp = self.client.im.v1.message.create(req)
            return resp.success()
        except Exception:
            return False

    def verify_event(self, headers: dict, body: str) -> Optional[dict]:
        try:
            import lark_oapi as lark

            event_handler = lark.EventDispatcherHandler.builder(
                config.feishu_app_id, config.feishu_app_secret
            ).build()

            return event_handler.do(headers, body)
        except Exception:
            return None
