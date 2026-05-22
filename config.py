# config.py
import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # 文件目录
    TEMP_DIR = os.getenv("TEMP_DIR", os.path.join(BASE_DIR, "temp"))
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
    RESULT_DIR = os.getenv("RESULT_DIR", os.path.join(BASE_DIR, "results"))
    REFERENCE_AUDIO_DIR = os.getenv(
        "REFERENCE_AUDIO_DIR",
        os.path.join(BASE_DIR, "reference_audio")
    )

    # 结果 URL 前缀：要和 app.py 里的路由对应
    RESULT_URL_PREFIX = os.getenv("RESULT_URL_PREFIX", "/results")

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB

    # Celery / Redis
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # 业务参数
    ALIGNMENT_THRESHOLD = float(os.getenv("ALIGNMENT_THRESHOLD", "0.8"))