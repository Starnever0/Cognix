import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.home_path = Path.home() / ".cognix"
        self.home_path.mkdir(exist_ok=True)
        
        self.db_path = self.home_path / "cognix.db"
        self.events_path = self.home_path / "events"
        self.events_path.mkdir(exist_ok=True)
        
        load_dotenv(self.home_path / ".env")
        
        self.feishu_app_id = os.getenv("FEISHU_APP_ID", "")
        self.feishu_app_secret = os.getenv("FEISHU_APP_SECRET", "")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_model = os.getenv("LLM_MODEL", "qwen3.5-35b")
        
        # Redis配置
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_db = int(os.getenv("REDIS_DB", 0))
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.short_term_ttl = int(os.getenv("SHORT_TERM_TTL", 3600))  # 短期记忆默认过期时间1小时
        
        # Autodream配置
        self.autodream_enabled = os.getenv("AUTODREAM_ENABLED", "false").lower() == "true"  # 默认关闭
        self.autodream_schedule_interval = int(os.getenv("AUTODREAM_SCHEDULE_INTERVAL", 24))  # 定时执行间隔，单位小时
        self.autodream_deduplication_threshold = float(os.getenv("AUTODREAM_DEDUPLICATION_THRESHOLD", 0.85))  # 去重相似度阈值

config = Config()
