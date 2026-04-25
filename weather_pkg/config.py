import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv() # 从 .env 文件加载环境变量

class Config:
    # 和风天气
    QWEATHER_API_HOST = os.getenv("QWEATHER_API_HOST", "https://mn5g7dweq9.re.qweatherapi.com")
    QWEATHER_KEY = os.getenv("QWEATHER_KEY")
    if not QWEATHER_KEY:
        raise RuntimeError("请在环境变量中设置 QWEATHER_KEY")

    # LLM
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_TEMP = float(os.getenv("LLM_TEMP", "0.3"))

    # SMTP
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.qq.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SENDER_NAME = os.getenv("SENDER_NAME","鱼松天气")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)

    # 数据目录
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
    DB_PATH = DATA_DIR / "weather.db"
    ARCHIVE_DIR = DATA_DIR / "archive"

    @classmethod
    def ensure_dirs(cls):
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)