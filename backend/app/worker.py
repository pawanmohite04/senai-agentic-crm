from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("senai_worker", broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task
def process_email_job(message_id: str) -> dict:
    return {"message_id": message_id, "status": "processed-by-sync-path"}
