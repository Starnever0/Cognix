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
        
        # LLM语义分类增强配置
        self.llm_classification_enabled = os.getenv("LLM_CLASSIFICATION_ENABLED", "false").lower() == "true"  # 默认关闭
        self.llm_classification_confidence_threshold = float(os.getenv("LLM_CLASSIFICATION_THRESHOLD", "0.7"))  # 低于该置信度才调用LLM
        
        # 上下文动态裁剪配置
        self.context_trim_enabled = os.getenv("CONTEXT_TRIM_ENABLED", "false").lower() == "true"  # 默认关闭，开启后减少70%+token消耗
        self.max_history_rounds = int(os.getenv("MAX_HISTORY_ROUNDS", "3"))  # 最多保留最近N轮对话
        self.max_relevant_memory = int(os.getenv("MAX_RELEVANT_MEMORY", "3"))  # 最多返回N条相关记忆

config = Config()
