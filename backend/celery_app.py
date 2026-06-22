# celery_app.py
from celery import Celery
from config import Config

celery = Celery(
    "video_processor",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=["task"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_transport_options={"connection_kwargs": {"protocol": 2}},
    result_backend_transport_options={"connection_kwargs": {"protocol": 2}},
)